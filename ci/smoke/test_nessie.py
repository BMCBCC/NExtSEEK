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
from ci.smoke.client import GuardedSession
from ci.smoke.conftest import _guard_context, login_storage_state

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

# The retrieve body (RetrieveRequest in nextseek_api/models.py). Its only required
# field is `query`, but a body naming neither session_id nor schema_url always
# answers SESSION_MISSING_OR_EXPIRED with no endpoints, so the check adds this
# instance's own schema URL. The server recognises that URL and builds the document
# in-process rather than fetching it (is_self_schema_url in
# nextseek_api/schema_rag/schema_processor.py), and ingests it on first use.
SCHEMA_RAG_QUERY = {"query": "list the samples in a project"}
SELF_SCHEMA_PATH = "/nextseek_api/schema/"


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


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #

_ADMIN_HELP = ("CI_WRITE_USER (the superuser in ~/.config/nextseek/ci.env) drives the "
               "Nessie lane")


@pytest.fixture(scope="module")
def nessie_admin_api(profile, base_url, write_creds) -> GuardedSession:
    """Basic-authenticated client for the write account, cookie-free for the reason
    the write lane's wapi fixture gives: a sessionid would outrank the Basic header."""
    s = GuardedSession(profile=profile, base_url=base_url)
    s.auth = write_creds
    s.headers["Accept"] = "application/json"
    return s


@pytest.fixture(scope="module")
def nessie_budget() -> ChatBudget:
    return ChatBudget()


@pytest.fixture(scope="module")
def nessie_evidence_dir(tmp_path_factory) -> Path:
    """startup/ci/runner.py names this through CI_NESSIE_EVIDENCE_DIR; a direct
    pytest run gets a temporary directory."""
    raw = os.environ.get("CI_NESSIE_EVIDENCE_DIR")
    path = Path(raw) if raw else tmp_path_factory.mktemp("nessie-evidence")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _module_failures(request) -> int:
    return request.session.testsfailed


@pytest.fixture(scope="module")
def nessie_context(request, browser, profile, base_url, write_creds, tmp_path_factory,
                   nessie_budget, nessie_evidence_dir):
    """A browser context logged in as the write account.

    Its network guard admits at most MAX_CHAT_POSTS chat POSTs (a further one is
    aborted and fails the lane) and aborts any other paid POST outright.
    """
    failed_before = _module_failures(request)
    state = login_storage_state(browser, profile, base_url, write_creds,
                                tmp_path_factory.mktemp("nessie-auth") / "state.json")
    ctx = browser.new_context(viewport={"width": 1440, "height": 900},
                              storage_state=state, base_url=base_url,
                              accept_downloads=True)
    _guard_context(ctx, profile)

    def _guard(route):
        verdict = classify_request(route.request.method, route.request.url)
        if verdict == "blocked" or (verdict == "lane" and not nessie_budget.admit_post()):
            return route.abort()
        return route.continue_()

    ctx.route("**/nextseek_api/**", _guard)
    ctx.tracing.start(screenshots=True, snapshots=True)
    yield ctx
    if _module_failures(request) > failed_before:
        ctx.tracing.stop(path=str(nessie_evidence_dir / "trace.zip"))
    else:
        ctx.tracing.stop()
    ctx.close()


@pytest.fixture(scope="module")
def nessie_page(request, nessie_context, base_url, nessie_evidence_dir):
    failed_before = _module_failures(request)
    page = nessie_context.new_page()
    page.goto(f"{base_url}/seek/assistant/", wait_until="domcontentloaded", timeout=120_000)
    page.get_by_test_id("chat-input").wait_for(state="visible", timeout=60_000)
    yield page
    if _module_failures(request) > failed_before:
        page.screenshot(path=str(nessie_evidence_dir / "page.png"), full_page=True)


# --------------------------------------------------------------------------- #
# stage 1: everything exists (no model call)
# --------------------------------------------------------------------------- #

def test_the_write_account_is_an_admin_in_a_participating_project(nessie_admin_api, base_url):
    r = nessie_admin_api.get(f"{base_url}/nextseek_api/assistant/me/", timeout=60)
    assert r.status_code != 403, (
        f"{_ADMIN_HELP}, and it is not in ASSISTANT_PARTICIPATING_PROJECTS "
        "(dmac/local_settings.py), so it cannot send a chat turn")
    assert r.status_code == 200, f"assistant/me answered {r.status_code}: {r.text[:200]}"
    assert r.json().get("is_admin") is True, f"{_ADMIN_HELP}, and it is not a superuser"


def test_the_smoke_account_is_not_an_admin(api, base_url):
    r = api.get(f"{base_url}/nextseek_api/assistant/me/", timeout=60)
    assert r.status_code == 200 and r.json().get("is_admin") is False


def test_the_chat_page_renders_every_control(nessie_page):
    # Imported here, not at module scope: test_nessie_unit.py imports this module
    # in the no-stack lane, which has no playwright.
    from playwright.sync_api import expect

    page = nessie_page
    page.get_by_test_id("new-chat-button").click()   # a fresh chat has no bundle
    for test_id in ("chat-input", "send-button", "new-chat-button", "upload-control"):
        assert page.get_by_test_id(test_id).first.is_visible(), f"{test_id} is not visible"
    assert page.get_by_label("Saved chats").count() >= 1, "the saved-chats sidebar is missing"
    page.get_by_label("Toggle debug panel").click()
    page.get_by_test_id("debug-panel").wait_for(state="visible", timeout=30_000)
    # Waiting assertions from here on. The sheet's controls are not all mounted the
    # moment the panel is: the route override renders only once the page's own
    # assistant/me call has set isAdmin, and an instant is_visible() lost that race
    # on the live stack.
    expect(page.locator("#route-override"),
           "the admin route override is missing for a superuser").to_be_visible(timeout=30_000)
    for test_id in ("json-download", "metadata-download"):
        button = page.get_by_test_id(test_id)
        message = f"{test_id} must be present and disabled before a chat has a bundle"
        expect(button, message).to_be_visible(timeout=30_000)
        expect(button, message).to_be_disabled(timeout=30_000)
    page.keyboard.press("Escape")


NESSIE_ROUTES = [
    r for r in routes.REGISTRY
    if r.path and "GET" in r.methods
    and r.pattern.startswith(tuple(f"^nextseek_api/^^{p}" for p in NESSIE_PREFIXES))
]


@pytest.mark.parametrize("route", NESSIE_ROUTES, ids=lambda r: r.path)
def test_every_nessie_route_answers(route, profile, base_url, anon, api, web, nessie_admin_api):
    """T0 for the Nessie surface, including the superuser-only routes T0 never
    requests (its sweep must never hold superuser; the pin is
    test_t0_never_sweeps_a_write_auth_route_under_any_profile)."""
    if profile not in route.profiles:
        pytest.skip(f"not enabled for {profile}")
    if "{" in route.path:
        pytest.skip("needs a discovered placeholder; T0 covers it")
    client = {"anon": anon, "smoke": api, "web": web, "write": nessie_admin_api}[route.auth]
    r = client.get(f"{base_url}{route.path}", timeout=60, allow_redirects=False)
    expected = route.expect if isinstance(route.expect, tuple) else (route.expect,)
    if route.xfail and r.status_code not in expected:
        pytest.xfail(route.xfail)
    assert r.status_code in expected, (
        f"{route.path} answered {r.status_code}, expected {expected}: {r.text[:200]}")


def test_sessions_test_cases_and_uploads_answer(nessie_admin_api, base_url):
    for path, key in (("assistant/sessions/", "sessions"), ("assistant/test-cases/", "test_cases"),
                      ("nessie/uploads/", "files")):
        r = nessie_admin_api.get(f"{base_url}/nextseek_api/{path}", timeout=60)
        assert r.status_code == 200 and key in r.json(), f"{path}: {r.status_code} {r.text[:200]}"


def test_schema_rag_retrieve_returns_endpoints(api, base_url):
    """It answers 200 even when retrieval failed, so the list is what is asserted.

    The list is `endpoints_minimal` in the default minimal mode (`endpoints_full` in
    full mode): RetrieveResponse in nextseek_api/models.py has no `endpoints` key.
    """
    body = {**SCHEMA_RAG_QUERY, "schema_url": f"{base_url}{SELF_SCHEMA_PATH}"}
    r = api.post(f"{base_url}/nextseek_api/schema_rag/retrieve/", json=body, timeout=120)
    assert r.status_code == 200, f"{r.status_code}: {r.text[:200]}"
    data = r.json()
    assert data.get("endpoints_minimal"), (
        f"no endpoints retrieved: message={data.get('message')!r} "
        f"error_code={(data.get('debug') or {}).get('error_code')!r}")


def test_a_scratch_session_is_created_renamed_and_deleted(nessie_admin_api, base_url):
    root = f"{base_url}/nextseek_api/assistant/sessions/"
    r = nessie_admin_api.post(root, json={}, timeout=60)
    assert r.status_code == 201, f"create: {r.status_code} {r.text[:200]}"
    sid = r.json()["session_id"]
    try:
        r = nessie_admin_api.patch(f"{root}{sid}/", json={"title": "ci nessie scratch"}, timeout=60)
        assert r.status_code == 200 and r.json().get("title") == "ci nessie scratch"
    finally:
        r = nessie_admin_api.delete(f"{root}{sid}/", timeout=60)
    assert r.status_code == 204, f"delete: {r.status_code}"
    assert nessie_admin_api.get(f"{root}{sid}/", timeout=60).status_code == 404
