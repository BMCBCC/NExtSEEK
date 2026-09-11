"""The Nessie lane: proves a build did not break Nessie.

Stage 1 checks that every Nessie route and chat-page control exists, with no model
call. Stages 2 and 3 type three NS questions and one CC question into the real
chat page, then check the results through the API, including whether the sessions
endpoints report what the page showed.

THIS IS THE FILE TO EXTEND when Nessie changes. A new question is a row in
QUESTIONS. A new endpoint is a registry entry in ci/routes.py plus a check here.
Spec: docs/superpowers/specs/2026-09-11-nessie-ci-lane-design.md.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ci import routes

pytestmark = [pytest.mark.nessie, pytest.mark.flow, pytest.mark.profiles("local", "dev")]


# --------------------------------------------------------------------------- #
# the questions
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Question:
    key: str
    text: str
    route: str          # the engine the router must pick: nextseek_query | container_cc
    path: str           # system | api | graph | cc
    bundle: bool        # the turn registers an NS bundle (JSON and Metadata downloads)
    cc_artifact: bool   # the turn leaves a Container-CC artifact


# NS first, CC last: a completed CC turn makes the chat sticky, so an NS question
# asked after it would be answered by CC.
QUESTIONS: tuple[Question, ...] = (
    Question("capabilities", "What can you do?", "nextseek_query", "system", False, False),
    Question("ndma_mice", "What mice are treated with NDMA?", "nextseek_query", "api", True, False),
    Question("impact_studies", "What studies are in IMPACT?", "nextseek_query", "graph", True, False),
    Question("nhp_graph", "Make me a graph of NHP species", "container_cc", "cc", False, True),
)

MAX_CHAT_POSTS = len(QUESTIONS)
SPEND_CEILING_USD = 1.00
CC_TURN_CAP_USD = 0.50            # NEXTSEEK_CC_MAX_BUDGET_USD's default
TURN_TIMEOUT_S = {"nextseek_query": 300, "container_cc": 240}
LANE_DEADLINE_S = 720
POLL_INTERVAL_S = 2.0
CHAT_PATH = "/nextseek_api/cc-assistant/query/async/"
GRAPH_MODE = "graph_query"       # the mode the NS graph branch records on its bundle
ROUTE_ENTRY_AGENT = "router"     # the Debug panel's agent label for a route_decided entry
NESSIE_PREFIXES = ("assistant/", "cc-assistant/", "nessie/", "evaluator/", "schema_rag/")


# --------------------------------------------------------------------------- #
# pure helpers (pinned by test_nessie_unit.py)
# --------------------------------------------------------------------------- #

def classify_request(method: str, url: str) -> str:
    """'lane' for the chat POST this lane sends, 'blocked' for any other paid POST,
    'pass' for everything else. Read from the registry, so a new paid route is
    blocked the day it is declared."""
    if (method or "").upper() != "POST":
        return "pass"
    route = routes.match(url)
    if route is None:
        return "pass"
    if route.lane == "nessie":
        return "lane"
    if route.exclude == "EXCLUDE_COST":
        return "blocked"
    return "pass"


class ChatBudget:
    """At most MAX_CHAT_POSTS chat POSTs, and the reported spend against the ceiling."""

    def __init__(self, max_posts: int = MAX_CHAT_POSTS,
                 ceiling_usd: float = SPEND_CEILING_USD) -> None:
        self.max_posts = max_posts
        self.ceiling_usd = ceiling_usd
        self.posts = 0
        self.refused = 0
        self.spent_usd = 0.0

    def admit_post(self) -> bool:
        if self.posts >= self.max_posts:
            self.refused += 1
            return False
        self.posts += 1
        return True

    def add_cost(self, usd: float | None) -> None:
        if usd is not None:
            self.spent_usd += float(usd)

    @property
    def over_ceiling(self) -> bool:
        return self.spent_usd > self.ceiling_usd


def first_event(progress: list, name: str) -> dict | None:
    for entry in progress or []:
        if isinstance(entry, dict) and entry.get("event") == name:
            return entry.get("data") or {}
    return None


def route_decision(progress: list) -> tuple[str | None, str | None]:
    data = first_event(progress, "route_decided") or {}
    return data.get("route"), data.get("source")


def cc_model_id(progress: list) -> str | None:
    data = first_event(progress, "cc_turn_meta")
    return None if data is None else data.get("model_id")


def query_error(progress: list) -> str | None:
    data = first_event(progress, "query_error")
    if data is None:
        return None
    return str(data.get("error") or data)


def is_terminal(status: str | None) -> bool:
    return status in ("completed", "error")


def reported_cost(result: dict | None) -> float | None:
    if not isinstance(result, dict):
        return None
    value = result.get("total_cost_usd")
    return float(value) if isinstance(value, (int, float)) else None


def bundle_path(mode: str | None) -> str:
    return "graph" if mode == GRAPH_MODE else "api"


def normalize(text: str) -> str:
    """Letters and digits only, lower case, single spaces."""
    return re.sub(r"[^0-9A-Za-z]+", " ", text or "").strip().lower()


def plain_prefix(text: str, n: int = 30) -> str:
    """The first n characters of the reply's first non-empty line, normalized:
    enough to find the same reply once the page has rendered its markdown."""
    for line in (text or "").splitlines():
        cleaned = normalize(line)
        if cleaned:
            return cleaned[:n].strip()
    return ""


@dataclass
class TurnRecord:
    key: str
    text: str
    expected_route: str
    task_id: str | None = None
    session_id: str | None = None
    status: str | None = None
    progress: list = field(default_factory=list)
    result: dict | None = None
    reply: str = ""
    bundle_id: int | None = None
    route: str | None = None
    source: str | None = None
    model_id: str | None = None
    cost_usd: float | None = None
    seconds: float | None = None
    error: str | None = None
    debug_agents: list = field(default_factory=list)     # Debug panel entries after the turn
    page_downloads: dict = field(default_factory=dict)   # {"json": filename, "metadata": filename}
    page_artifacts: int = 0                              # artifact links the page rendered


_SUMMARY_FIELDS = ("key", "text", "expected_route", "route", "source", "task_id",
                   "session_id", "status", "seconds", "cost_usd", "error")


def summary_payload(records: list, budget: ChatBudget, kept_session: dict | None,
                    evidence_dir: str | None) -> dict:
    """What the lane reports to the CI record (startup/ci/runner.py renders it)."""
    return {
        "questions": [{k: getattr(r, k) for k in _SUMMARY_FIELDS} for r in records],
        "posts": budget.posts,
        "refused_posts": budget.refused,
        "spent_usd": round(budget.spent_usd, 4),
        "ceiling_usd": budget.ceiling_usd,
        "kept_session": kept_session,
        "evidence_dir": evidence_dir,
    }
