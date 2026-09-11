# Nessie CI lane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `ci/smoke` lane that proves a build did not break Nessie: every Nessie route and chat-page element exists, three NS questions and one CC question complete through the real chat page, and the sessions endpoints report what the page showed.

**Architecture:** One test module, `ci/smoke/test_nessie.py`, holds the question table, the lane's pure helpers, its fixtures and every check, so that a Nessie change means editing one file. It rides the existing smoke machinery (the registry, `GuardedSession`, the browser fixtures, the readiness gate, the CI record) and adds three switches: a registry `lane` tag on the one chat route the page posts to, a `--no-nessie` pytest option, and startup flags that turn the lane on after an app rebuild on `local` and `dev`.

**Tech Stack:** pytest, requests and Playwright (the smoke lane's only dependencies), Typer (startup CLI), React + Vite + vitest + Playwright (the chat frontend).

**Spec:** `docs/superpowers/specs/2026-09-11-nessie-ci-lane-design.md`. Read it before any task.

## Global Constraints

- Work in the worktree `<worktree>`, branch `feat/nessie-ci-lane`, based on `origin/dev` at `f1ef0f3c`. Never push.
- `ci/routes.py` imports the standard library only.
- The smoke lane runs under `uv run --no-project --with pytest --with requests --with playwright`: `ci/smoke/` may import pytest, requests, playwright, the standard library and `ci/` modules, nothing else.
- `startup/` never imports `ci/`. It passes information to the suite through command-line flags and environment variables, and reads results back from files.
- Never send a chat turn while implementing or verifying (no model spend). Stage 1 may be run live against the operator's local stack only with `--nessie-no-turns`. The paid live run belongs to the operator.
- Never rebuild images, restart or recreate containers, or run `./startup.sh rebuild`. Throwaway `docker run --rm` test containers are allowed.
- Never select tests with `-m` to opt out of Nessie: any `-m` switches the write lane back on (`ci/smoke/conftest.py`, `pytest_collection_modifyitems`).
- The spec's numbers, verbatim: 4 questions; at most 4 chat POSTs per run; reported spend ceiling $1.00; CC per-turn cap $0.50 (existing); NS turn timeout 300 s; CC turn timeout 240 s; lane deadline 720 s.
- Public repository: no credentials, tokens, personal home paths or email addresses in any tracked file. Never print the proxy token; check its length only.
- No em-dashes in anything written (docs, comments, messages). Stage files by name, never `git add -A` (`.gitattributes` keeps bytes as-is).
- Commit messages: conventional, with a module scope (`feat(ci): ...`, `feat(startup): ...`, `feat(chat_frontend): ...`, `docs(ci): ...`), ending with exactly these two lines:

```
Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SYnStRp5c97GtpBMyekMDM
```

## Commands used throughout

```bash
# No-stack smoke lane (no stack, no credentials, no browser)
CI_BOX_PROFILE=local uv run --no-project --with pytest --with requests \
  pytest ci/smoke/test_registry_unit.py ci/smoke/test_registry_contents.py \
         ci/smoke/test_guard_unit.py ci/smoke/test_profile_unit.py \
         ci/smoke/test_assertions_unit.py ci/smoke/test_readiness_unit.py \
         ci/smoke/test_terminal_unit.py ci/smoke/test_nessie_unit.py -q

# Startup lane
cd startup && uv run --project . --group test python -m pytest tests/ -q \
  -p no:nextseek_api.attributes.tests.attribute_fixtures \
  --ignore=tests/test_schema_fixups.py; cd ..

# Gate lane (Django), in the pre-move image that matches origin/dev
mkdir -p schema_rag/duckdb schema_rag/embedding_models
docker run --rm -i --network none -e LOG_DIR=/tmp/l \
  -e DJANGO_SETTINGS_MODULE=dmac.test_settings -e PYTHONDONTWRITEBYTECODE=1 \
  -v "$PWD":/src:ro -w /src "<the pre-move app image>" \
  /app/.venv/bin/python -m pytest ci/gate -q -p no:cacheprovider

# Frontend
cd chat_frontend && npm ci && npm test && npx playwright test --project mock; cd ..

# Stage 1 live (free), against the operator's running local stack
PORT=$(python3 -c "import json;print(json.load(open('<main checkout>/startup/.instance.json'))['ports']['nextseek'])")
CI_BOX_PROFILE=local uv run --no-project --with pytest --with requests --with playwright \
  pytest ci/smoke/test_nessie.py --base-url "http://127.0.0.1:$PORT" --nessie-no-turns -q
```

The running local stack serves the NessieAI refactor build, not this branch. Until the operator rebuilds from a tree that contains this branch, the page checks that need the new `data-testid`s (Task 4) fail in a live stage 1 run. That is expected; every other stage 1 check must pass.

---

### Task 1: Tag the lane's chat route in the registry

**Files:**
- Modify: `ci/routes.py` (the `Route` dataclass; the `cc-assistant/query/async/` entry; the `nessie/sessions/<id>/debug/` entry; the three `assistant/sessions/` notes)
- Test: `ci/smoke/test_registry_contents.py`

**Interfaces:**
- Produces: `Route.lane: str = ""`; `LANES = frozenset({"nessie"})`; `routes.lane_routes(lane: str) -> list[Route]`.

- [ ] **Step 1: Write the failing tests** (append to `ci/smoke/test_registry_contents.py`)

```python
def test_exactly_one_route_is_sent_by_a_lane_and_it_is_the_chat_turn():
    from ci.routes import lane_routes
    tagged = [r for r in REGISTRY if r.lane]
    assert [r.pattern for r in tagged] == [
        r"^nextseek_api/^^cc-assistant/query/async/$"
    ], f"lane-tagged routes: {[r.pattern for r in tagged]}"
    assert lane_routes("nessie") == tagged


def test_a_lane_route_stays_out_of_reach_of_the_sweep_and_the_guard():
    """The lane's browser sends this route; T0 and GuardedSession never do."""
    for route in REGISTRY:
        if route.lane:
            assert route.path is None and not route.profiles
            assert route.exclude == "EXCLUDE_COST"


def test_an_unknown_lane_is_refused():
    from ci.routes import Route
    with pytest.raises(ValueError, match="lane"):
        Route(pattern=r"^x/$", path=None, methods=(), profiles="",
              exclude="EXCLUDE_COST", lane="nightly")
```

(`pytest` is already imported at the top of that file; add the import if it is not.)

- [ ] **Step 2: Run them to see them fail**

Run the no-stack smoke lane (drop `test_nessie_unit.py` from the list until Task 3 creates it). Expected: 3 failures, `Route.__init__() got an unexpected keyword argument 'lane'` or `ImportError: lane_routes`.

- [ ] **Step 3: Implement**

In `ci/routes.py`, below `EXCLUDE_CODES`:

```python
# A lane is a named test module that sends a route OUTSIDE the T0 sweep and the
# requests-client guard: today only the Nessie lane's browser, which posts the one
# chat turn a person would send. The route keeps path=None and its exclude code,
# so nothing that iterates the registry can form a request for it.
LANES = frozenset({"nessie"})
```

In the `Route` dataclass, after `prod_allows_non_get`:

```python
    lane: str = ""                    # a lane that sends this route; see LANES
```

In `Route.__post_init__`, next to the exclude-code check:

```python
        if self.lane and self.lane not in LANES:
            raise ValueError(
                f"{self.pattern}: lane must be one of {sorted(LANES)}, not {self.lane!r}"
            )
```

At module level, next to `match()`:

```python
def lane_routes(lane: str) -> list[Route]:
    """The routes a named lane sends outside the sweep, in registry order."""
    return [r for r in REGISTRY if r.lane == lane]
```

On the `cc-assistant/query/async/` entry add `lane="nessie"` and extend its note:

```python
    Route(pattern=r"^nextseek_api/^^cc-assistant/query/async/$", path=None,
          methods=(), profiles="", auth="smoke", exclude="EXCLUDE_COST", lane="nessie",
          note="the router-dispatched chat turn; either engine may answer it. The "
               "Nessie lane's browser sends it (ci/smoke/test_nessie.py), at most "
               "four times per run; nothing else in CI does"),
```

On the `nessie/sessions/<id>/debug/` entry: read `nextseek_api/services/nessie.py` (`NessieViewSet.debug`, around line 97) and `nextseek_api/assistant/session_debug.py` to confirm that an id matching neither a session nor a task answers 404. Then change `expect=200` to `expect=404` and the note to `"unknown id: proves the route resolves and denies; superuser only, so the Nessie lane requests it with the write account"`. If it does not answer 404, keep `expect` as it is and record that in the commit body.

On the three `assistant/sessions/` entries, correct the notes. Today they say the write lane or the destructive lane sends POST, PATCH and DELETE, which no test does. Write: `"also accepts POST (PATCH and DELETE on a session), which the Nessie lane sends on local and dev for its scratch session and its cleanup"`.

- [ ] **Step 4: Run the no-stack smoke lane.** Expected: all pass, including the three new tests. `OWNED_ROUTE_COUNT` is unchanged: no route was added.

- [ ] **Step 5: Commit**

```bash
git add ci/routes.py ci/smoke/test_registry_contents.py
git commit -F - <<'EOF'
feat(ci): tag the chat turn the Nessie lane's browser sends

<body: the lane field, the debug entry's expect, the corrected session notes>

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SYnStRp5c97GtpBMyekMDM
EOF
```

---

### Task 2: Selection switches: the `nessie` markers and `--no-nessie`

**Files:**
- Modify: `ci/smoke/pytest.ini` (markers), `ci/smoke/conftest.py` (`pytest_addoption`, `pytest_configure`, `pytest_collection_modifyitems`, new pure function)
- Test: `ci/smoke/test_nessie_unit.py` (create)

**Interfaces:**
- Produces: markers `nessie` (the whole lane) and `nessie_turn` (anything that needs a chat turn); options `--no-nessie`, `--nessie-no-turns`; `conftest.nessie_skip_reason(keywords, *, no_nessie: bool, no_turns: bool) -> str | None`.

- [ ] **Step 1: Write the failing tests** (create `ci/smoke/test_nessie_unit.py`)

```python
"""No-stack tests for the Nessie lane: its selection switches and its pure helpers.

Stack-free by design, like the other *_unit.py files: no network, no credentials,
no browser.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ci.smoke.conftest import nessie_skip_reason


@pytest.mark.parametrize("keywords, no_nessie, no_turns, expected", [
    ({"test_x"}, True, True, None),                               # not a Nessie test
    ({"nessie"}, False, False, None),                             # the lane runs
    ({"nessie"}, True, False, "Nessie lane skipped by --no-nessie"),
    ({"nessie", "nessie_turn"}, True, True, "Nessie lane skipped by --no-nessie"),
    ({"nessie", "nessie_turn"}, False, True, "chat turns skipped by --nessie-no-turns"),
    ({"nessie"}, False, True, None),                              # stage 1 still runs
])
def test_nessie_skip_reason(keywords, no_nessie, no_turns, expected):
    assert nessie_skip_reason(keywords, no_nessie=no_nessie, no_turns=no_turns) == expected


def test_the_nessie_switch_is_not_a_mark_expression():
    """-m re-admits the write lane; the Nessie switch must never need one."""
    import ci.smoke.conftest as conftest
    source = Path(conftest.__file__).read_text()
    gate = source.index("def pytest_collection_modifyitems")
    early_return = source.index('if config.getoption("-m"):', gate)
    nessie_gate = source.index("nessie_skip_reason(", gate)
    assert nessie_gate < early_return, (
        "the Nessie gate must run before the -m early return, or --no-nessie "
        "stops working whenever someone passes -m"
    )
```

- [ ] **Step 2: Run** `CI_BOX_PROFILE=local uv run --no-project --with pytest --with requests pytest ci/smoke/test_nessie_unit.py -q`. Expected: ImportError on `nessie_skip_reason`.

- [ ] **Step 3: Implement**

`ci/smoke/pytest.ini`, under `markers =` (keep the existing two):

```ini
    nessie: the Nessie lane (ci/smoke/test_nessie.py). On by default on local and dev; --no-nessie skips it.
    nessie_turn: needs a real chat turn (model spend). --nessie-no-turns skips it.
```

`ci/smoke/conftest.py`, in `pytest_addoption` after `--force-profile`:

```python
    g.addoption("--no-nessie", action="store_true",
                help="Skip the Nessie lane (ci/smoke/test_nessie.py). Never use -m "
                     "for this: any -m expression re-admits the write lane.")
    g.addoption("--nessie-no-turns", action="store_true",
                help="Run only the Nessie lane's stage 1: no chat turn, no model "
                     "spend. For iterating on the lane itself.")
```

In `pytest_configure`, next to the existing markers:

```python
    config.addinivalue_line("markers", "nessie: the Nessie lane.")
    config.addinivalue_line("markers", "nessie_turn: needs a real chat turn.")
```

A new pure function above `pytest_collection_modifyitems`:

```python
def nessie_skip_reason(keywords, *, no_nessie: bool, no_turns: bool) -> str | None:
    """Why a Nessie-lane item is skipped, or None when it runs.

    Pure, so the no-stack lane can pin it. Applied before the -m early return in
    pytest_collection_modifyitems, which is what keeps the write lane deselected:
    a -m expression would switch that lane back on, so the Nessie switches are
    options, never mark expressions.
    """
    if "nessie" not in keywords:
        return None
    if no_nessie:
        return "Nessie lane skipped by --no-nessie"
    if no_turns and "nessie_turn" in keywords:
        return "chat turns skipped by --nessie-no-turns"
    return None
```

In `pytest_collection_modifyitems`, after the profile loop and **before** `if config.getoption("-m"):`:

```python
    no_nessie = config.getoption("--no-nessie")
    no_turns = config.getoption("--nessie-no-turns")
    for item in items:
        reason = nessie_skip_reason(item.keywords, no_nessie=no_nessie, no_turns=no_turns)
        if reason:
            item.add_marker(pytest.mark.skip(reason=reason))
```

Add one sentence to the function's docstring naming the third gate.

- [ ] **Step 4: Run** `ci/smoke/test_nessie_unit.py` and the no-stack smoke lane. Expected: all pass.

- [ ] **Step 5: Commit** `feat(ci): switch the Nessie lane with options, never with -m` (stage `ci/smoke/pytest.ini ci/smoke/conftest.py ci/smoke/test_nessie_unit.py`).

---

### Task 3: The lane's question table and pure helpers

**Files:**
- Create: `ci/smoke/test_nessie.py` (the data model and pure helpers only; Tasks 5 and 6 add fixtures and tests)
- Test: `ci/smoke/test_nessie_unit.py` (append)

**Interfaces:**
- Consumes: `ci.routes.match`, `Route.lane` (Task 1).
- Produces, all importable from `ci.smoke.test_nessie`: `Question`, `QUESTIONS`, `MAX_CHAT_POSTS`, `SPEND_CEILING_USD`, `CC_TURN_CAP_USD`, `TURN_TIMEOUT_S`, `LANE_DEADLINE_S`, `POLL_INTERVAL_S`, `CHAT_PATH`, `GRAPH_MODE`, `ROUTE_ENTRY_AGENT`, `NESSIE_PREFIXES`, `classify_request(method, url) -> str`, `ChatBudget`, `first_event(progress, name)`, `route_decision(progress) -> tuple[str | None, str | None]`, `cc_model_id(progress)`, `query_error(progress)`, `is_terminal(status) -> bool`, `reported_cost(result) -> float | None`, `bundle_path(mode) -> str`, `normalize(text) -> str`, `plain_prefix(text, n=30) -> str`, `TurnRecord`, `summary_payload(records, budget, kept_session, evidence_dir) -> dict`.

- [ ] **Step 1: Write the failing tests** (append to `ci/smoke/test_nessie_unit.py`)

```python
from ci.smoke.test_nessie import (
    CHAT_PATH, MAX_CHAT_POSTS, QUESTIONS, SPEND_CEILING_USD, ChatBudget, TurnRecord,
    bundle_path, cc_model_id, classify_request, is_terminal, normalize, plain_prefix,
    query_error, reported_cost, route_decision, summary_payload,
)

BASE = "http://127.0.0.1:8000"


def test_the_questions_are_three_ns_then_one_cc_with_unique_keys():
    assert [q.route for q in QUESTIONS] == [
        "nextseek_query", "nextseek_query", "nextseek_query", "container_cc"]
    assert [q.path for q in QUESTIONS] == ["system", "api", "graph", "cc"]
    assert len({q.key for q in QUESTIONS}) == len(QUESTIONS)
    assert MAX_CHAT_POSTS == len(QUESTIONS) == 4
    assert SPEND_CEILING_USD == 1.00


def test_classify_request():
    assert classify_request("POST", BASE + CHAT_PATH) == "lane"
    assert classify_request("GET", BASE + CHAT_PATH) == "pass"
    assert classify_request("POST", BASE + "/nextseek_api/nessie/query/") == "blocked"
    assert classify_request("POST", BASE + "/nextseek_api/cc-assistant/cc/query/async/") == "blocked"
    assert classify_request("POST", BASE + "/nextseek_api/assistant/sessions/") == "pass"
    assert classify_request("POST", BASE + "/login/") == "pass"


def test_chat_budget_refuses_the_fifth_post_and_tracks_spend():
    b = ChatBudget()
    assert [b.admit_post() for _ in range(5)] == [True, True, True, True, False]
    assert (b.posts, b.refused) == (4, 1)
    b.add_cost(0.24)
    b.add_cost(None)
    assert b.spent_usd == pytest.approx(0.24) and not b.over_ceiling
    b.add_cost(0.80)
    assert b.over_ceiling


PROGRESS = [
    {"event": "route_decided", "data": {"route": "container_cc", "source": "baml"}},
    {"event": "cc_turn_meta", "data": {"model_id": "us.anthropic.claude-opus-4-8"}},
    {"event": "query_complete", "data": {"reply": "done"}},
]


def test_progress_parsers():
    assert route_decision(PROGRESS) == ("container_cc", "baml")
    assert route_decision([]) == (None, None)
    assert cc_model_id(PROGRESS) == "us.anthropic.claude-opus-4-8"
    assert cc_model_id([]) is None
    assert query_error(PROGRESS) is None
    assert query_error([{"event": "query_error", "data": {"error": "403 path not permitted"}}]) \
        == "403 path not permitted"


def test_status_cost_and_path_helpers():
    assert is_terminal("completed") and is_terminal("error")
    assert not is_terminal("running") and not is_terminal(None)
    assert reported_cost({"total_cost_usd": 0.21}) == 0.21
    assert reported_cost({"reply": "x"}) is None and reported_cost(None) is None
    assert bundle_path("graph_query") == "graph"
    assert bundle_path("new_search") == "api"


def test_reply_matching_survives_markdown():
    reply = "**NDMA-treated mice**: 12 found\n\n| id | sex |"
    assert plain_prefix(reply) == "ndma treated mice 12 found"
    assert plain_prefix(reply) in normalize("NDMA-treated mice: 12 found  | id | sex |")
    assert plain_prefix("") == ""


def test_summary_payload_shape():
    rec = TurnRecord(key="nhp_graph", text="t", expected_route="container_cc",
                     route="container_cc", source="baml", task_id="a", session_id="s",
                     status="completed", seconds=88.0, cost_usd=0.24)
    b = ChatBudget()
    b.admit_post()
    b.add_cost(0.24)
    out = summary_payload([rec], b, None, "/tmp/e")
    assert out["posts"] == 1 and out["spent_usd"] == 0.24 and out["ceiling_usd"] == 1.0
    assert out["questions"][0]["key"] == "nhp_graph"
    assert out["questions"][0]["expected_route"] == "container_cc"
    assert out["kept_session"] is None and out["evidence_dir"] == "/tmp/e"
```

- [ ] **Step 2: Run** `ci/smoke/test_nessie_unit.py`. Expected: ImportError on `ci.smoke.test_nessie`.

- [ ] **Step 3: Implement** (create `ci/smoke/test_nessie.py`; no Playwright import at module scope, so the no-stack lane can import it)

```python
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
```

Before committing, confirm `ROUTE_ENTRY_AGENT` against `NessieAI/chat_frontend/src/lib/debugEntries.ts` (the label the Debug panel gives a `route_decided` event) and `GRAPH_MODE` against the graph branch of `NessieAI/chat_nextseek/src/chat_nextseek/orchestrator.py` (`mode="graph_query"`). If either differs, change the constant and the unit test together.

- [ ] **Step 4: Run** the no-stack smoke lane (now including `test_nessie_unit.py`). Expected: all pass. Also run `CI_BOX_PROFILE=local uv run --no-project --with pytest --with requests pytest ci/smoke/test_nessie.py --collect-only -q`: expected "no tests collected" with no error.

- [ ] **Step 5: Commit** `feat(ci): the Nessie lane's questions and pure helpers`.

---

### Task 4: Frontend test ids, the mock URL, and the rebuilt bundle

**Files:**
- Modify: `NessieAI/chat_frontend/src/components/Layout/RightSidebar.tsx`, `NessieAI/chat_frontend/src/components/DebugPanel/DebugPanel.tsx`, `NessieAI/chat_frontend/src/components/Sessions/SessionListItem.tsx`, `NessieAI/chat_frontend/e2e/fixtures/ws-mock.ts`
- Test: `NessieAI/chat_frontend/src/components/__tests__/testIds.test.tsx` (create; follow the render setup the existing tests under `src/components/**/__tests__/` use)
- Rebuilt: `static/js/chat_assistant/` (second commit)

**Interfaces:**
- Produces, for Tasks 5 and 6: `data-testid="json-download"`, `data-testid="metadata-download"`, `data-testid="debug-panel"` (on both the empty state and the list), `data-testid="debug-entry"` with `data-agent={entry.agent}`, `data-testid="session-item"` with `data-session-id`. Existing ids stay: `chat-input`, `send-button`, `new-chat-button`, `upload-control`, `message-bubble` (with `data-role`), `artifact-download`, `#route-override`, the "Toggle debug panel" and "Saved chats" labels.

(This refines the spec's `data-kind`: the panel's own `entry.agent` label is carried as `data-agent`, so no second vocabulary is invented.)

- [ ] **Step 1: Write the failing test** (`testIds.test.tsx`)

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RightSidebar } from "@/components/Layout/RightSidebar";
import { DebugPanel } from "@/components/DebugPanel/DebugPanel";

const noBundle = { entries: [], bundleId: null } as never;
const withEntry = {
  entries: [{ agent: "router", summary: "nextseek_query (baml)", timestamp: new Date() }],
  bundleId: 3,
} as never;

describe("test ids the Nessie CI lane relies on", () => {
  it("download buttons exist and are disabled without a bundle", () => {
    render(<RightSidebar isOpen onOpenChange={() => {}} debugData={noBundle} onDownload={() => {}} />);
    expect(screen.getByTestId("json-download")).toBeDisabled();
    expect(screen.getByTestId("metadata-download")).toBeDisabled();
  });

  it("the debug panel and each entry are addressable", () => {
    render(<DebugPanel debugData={withEntry} />);
    expect(screen.getByTestId("debug-panel")).toBeInTheDocument();
    expect(screen.getByTestId("debug-entry")).toHaveAttribute("data-agent", "router");
  });

  it("the empty debug panel is addressable too", () => {
    render(<DebugPanel debugData={noBundle} />);
    expect(screen.getByTestId("debug-panel")).toBeInTheDocument();
  });
});
```

Match `DebugData`'s real field names from `src/lib/types/chat.ts` and the `toBeDisabled` matcher setup from the existing tests (`@testing-library/jest-dom`). If the repo's tests import differently, follow them.

- [ ] **Step 2: Run** `cd chat_frontend && npm test -- testIds`. Expected: fails on the missing test ids.

- [ ] **Step 3: Implement**
  - `RightSidebar.tsx`: add `data-testid="json-download"` to the JSON `<Button>` and `data-testid="metadata-download"` to the Metadata one.
  - `DebugPanel.tsx`: add `data-testid="debug-panel"` to the empty-state `<div>` and to `<Accordion>`; add `data-testid="debug-entry" data-agent={entry.agent}` to each `<AccordionItem>`.
  - `SessionListItem.tsx`: add `data-testid="session-item" data-session-id={...}` to the row's root element, using the session id prop the component already has.
  - `e2e/fixtures/ws-mock.ts`: change `**/nextseek_api/assistant/query/async/` (and its comment) to `**/nextseek_api/cc-assistant/query/async/`, the URL `src/lib/services/chatApi.ts` posts to.

- [ ] **Step 4: Run** `npm ci && npm test && npx playwright test --project mock` in `NessieAI/chat_frontend/`. Expected: vitest green; the mock project green (the specs that failed only because of the stale URL now pass; list any spec that still fails and why in the commit body).

- [ ] **Step 5: Commit the source** `feat(chat_frontend): test ids for the Nessie CI lane; point the mock at the live chat URL` (stage the four source files and the new test).

- [ ] **Step 6: Rebuild and commit the bundle.** `cd chat_frontend && npm run build:embedded`. Check `git status --short static/js/chat_assistant/` shows only the rebuilt bundle files, including the Vite manifest the template reads. Stage exactly those paths and commit `build(chat_frontend): rebuild the embedded bundle for the new test ids`. The Docker build has no npm step, so this committed bundle is what ships.

---

### Task 5: Stage 1: every Nessie route and page control exists

**Files:**
- Modify: `ci/smoke/conftest.py` (extract the browser login into a helper), `ci/smoke/test_nessie.py` (fixtures and stage 1 tests)

**Interfaces:**
- Consumes: Task 1 (`routes.REGISTRY`, the corrected debug entry), Task 2 (markers, `--nessie-no-turns`), Task 3 (constants, `ChatBudget`, `classify_request`), Task 4 (test ids).
- Produces, for Task 6: fixtures `nessie_admin_api` (module), `nessie_budget` (module), `nessie_evidence_dir` (module), `nessie_context` (module), `nessie_page` (module); `conftest.login_storage_state(browser, profile, base_url, creds, path) -> str`.

- [ ] **Step 1: Extract the browser login in `ci/smoke/conftest.py`** so the Nessie lane can log in as the write account without copying it:

```python
def login_storage_state(browser, profile: str, base_url: str,
                        creds: tuple[str, str], path: Path) -> str:
    """Log in once through /login/ in a real browser; save and return the cookies.

    Session cookie only, never an HTTP Basic header on the context: see
    storage_state below for why.
    """
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    _guard_context(ctx, profile)
    page = ctx.new_page()
    page.goto(f"{base_url}/login/", wait_until="domcontentloaded")
    page.fill("input#username", creds[0])
    page.fill("input#password", creds[1])
    with page.expect_navigation(wait_until="domcontentloaded", timeout=120_000):
        page.click("button[type=submit].auth-submit")
    assert "/login" not in page.url, (
        f"still on the login page after submitting as {creds[0]}: {page.url}"
    )
    ctx.storage_state(path=str(path))
    ctx.close()
    return str(path)
```

and make the existing `storage_state` fixture call it:

```python
@pytest.fixture(scope="session")
def storage_state(browser, profile, base_url, smoke_creds, tmp_path_factory):
    """<keep the existing docstring>"""
    path = tmp_path_factory.mktemp("auth") / "state.json"
    return login_storage_state(browser, profile, base_url, smoke_creds, path)
```

Run the no-stack smoke lane: still green.

- [ ] **Step 2: Add the fixtures to `ci/smoke/test_nessie.py`**

```python
from ci.smoke.client import GuardedSession
from ci.smoke.conftest import _guard_context, login_storage_state

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
```

- [ ] **Step 3: Add the stage 1 tests to `ci/smoke/test_nessie.py`**

```python
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
    page = nessie_page
    page.get_by_test_id("new-chat-button").click()   # a fresh chat has no bundle
    for test_id in ("chat-input", "send-button", "new-chat-button", "upload-control"):
        assert page.get_by_test_id(test_id).first.is_visible(), f"{test_id} is not visible"
    assert page.get_by_label("Saved chats").count() >= 1, "the saved-chats sidebar is missing"
    page.get_by_label("Toggle debug panel").click()
    page.get_by_test_id("debug-panel").wait_for(state="visible", timeout=30_000)
    assert page.locator("#route-override").is_visible(), (
        "the admin route override is missing for a superuser")
    for test_id in ("json-download", "metadata-download"):
        button = page.get_by_test_id(test_id)
        assert button.is_visible() and button.is_disabled(), (
            f"{test_id} must be present and disabled before a chat has a bundle")
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
    """It answers 200 even when retrieval failed, so the list is what is asserted."""
    r = api.post(f"{base_url}/nextseek_api/schema_rag/retrieve/",
                 json=SCHEMA_RAG_QUERY, timeout=120)
    assert r.status_code == 200, f"{r.status_code}: {r.text[:200]}"
    assert r.json().get("endpoints"), f"no endpoints retrieved: {r.text[:300]}"


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
```

Define `SCHEMA_RAG_QUERY` with the constants block, after reading the retrieve request model (`nextseek_api/services/schema_rag.py`, the `retrieve` action, and its pydantic request class in `nextseek_api/models.py`): a dict with the minimum required fields and a query such as `"list the samples in a project"`. Likewise confirm the create body for `assistant/sessions/` (`nextseek_api/services/assistant.py`, `AssistantViewSet`, the sessions `create`), and the PATCH field name for the title.

- [ ] **Step 4: Verify**
  - No-stack smoke lane: green.
  - `pytest ci/smoke/test_nessie.py --collect-only -q`: stage 1 tests collected; no error.
  - Stage 1 live (the command at the top, with `--nessie-no-turns`): every test passes except the page checks that need Task 4's test ids, which fail against the running (older) bundle. Record exactly which ones failed and why in the commit body.

- [ ] **Step 5: Commit** `feat(ci): Nessie lane stage 1, every Nessie route and chat control exists` (stage `ci/smoke/conftest.py ci/smoke/test_nessie.py`).

---

### Task 6: Stages 2 and 3: the four questions, the cross-check, cleanup and evidence

**Files:**
- Modify: `ci/smoke/test_nessie.py`

**Interfaces:**
- Consumes: everything from Tasks 3 and 5.
- Produces, for Task 7: the JSON file named by `CI_NESSIE_SUMMARY` (the `summary_payload` shape), written at module teardown when the variable is set; evidence files (`trace.zip`, `page.png`, `debug.json`) in `nessie_evidence_dir` on failure.

- [ ] **Step 1: The `chat_run` fixture** (sends the questions; every test below reads its records)

```python
# --------------------------------------------------------------------------- #
# stages 2 and 3: the questions, asked in the page and checked through the API
# --------------------------------------------------------------------------- #

def _poll(api, base_url: str, rec: TurnRecord, timeout_s: int) -> None:
    deadline = time.monotonic() + timeout_s
    url = f"{base_url}/nextseek_api/nessie/tasks/{rec.task_id}/progress/"
    while True:
        r = api.get(url, timeout=60)
        assert r.status_code == 200, f"{rec.key}: progress answered {r.status_code}"
        body = r.json()
        rec.status, rec.progress, rec.result = body["status"], body["progress"], body.get("result")
        if is_terminal(rec.status):
            return
        if time.monotonic() > deadline:
            rec.error = f"no terminal status after {timeout_s} s (last: {rec.status})"
            return
        time.sleep(POLL_INTERVAL_S)


def _open_debug(page) -> None:
    if not page.get_by_test_id("debug-panel").is_visible():
        page.get_by_label("Toggle debug panel").click()
        page.get_by_test_id("debug-panel").wait_for(state="visible", timeout=30_000)


def _page_download(page, test_id: str, directory: Path) -> str:
    button = page.get_by_test_id(test_id)
    assert button.is_enabled(), f"{test_id} is still disabled after a bundle turn"
    with page.expect_download(timeout=60_000) as got:
        button.click()
    target = directory / got.value.suggested_filename
    got.value.save_as(str(target))
    json.loads(target.read_text())          # it must be JSON
    return got.value.suggested_filename


@pytest.fixture(scope="module")
def chat_run(request, nessie_page, nessie_admin_api, base_url, nessie_budget,
             nessie_evidence_dir, tmp_path_factory):
    if request.config.getoption("--nessie-no-turns"):
        pytest.skip("chat turns skipped by --nessie-no-turns")
    failed_before = _module_failures(request)
    page = nessie_page
    downloads = tmp_path_factory.mktemp("nessie-downloads")
    page.get_by_test_id("new-chat-button").click()
    records: list[TurnRecord] = []
    started = time.monotonic()
    assistant_bubbles = page.locator('[data-testid="message-bubble"][data-role="assistant"]')

    for q in QUESTIONS:
        assert time.monotonic() - started < LANE_DEADLINE_S, (
            f"the lane passed its {LANE_DEADLINE_S} s deadline before asking {q.key}")
        rec = TurnRecord(key=q.key, text=q.text, expected_route=q.route)
        records.append(rec)
        page.get_by_test_id("chat-input").fill(q.text)
        with page.expect_response(
            lambda r: urlsplit(r.url).path == CHAT_PATH and r.request.method == "POST",
            timeout=60_000,
        ) as got:
            page.get_by_test_id("send-button").click()
        assert got.value.status == 202, f"{q.key}: the chat POST answered {got.value.status}"
        body = got.value.json()
        rec.task_id, rec.session_id = body["task_id"], body["session_id"]

        t0 = time.monotonic()
        _poll(nessie_admin_api, base_url, rec, TURN_TIMEOUT_S[q.route])
        rec.seconds = round(time.monotonic() - t0, 1)
        rec.route, rec.source = route_decision(rec.progress)
        rec.model_id = cc_model_id(rec.progress)
        rec.error = rec.error or query_error(rec.progress)
        if isinstance(rec.result, dict):
            rec.reply = rec.result.get("reply") or ""
            rec.bundle_id = rec.result.get("bundle_id")
        rec.cost_usd = reported_cost(rec.result)
        nessie_budget.add_cost(rec.cost_usd)

        # The page must render the reply before the next question is typed.
        assistant_bubbles.nth(len(records) - 1).wait_for(state="visible", timeout=60_000)
        _open_debug(page)
        rec.debug_agents = [
            e.get_attribute("data-agent")
            for e in page.get_by_test_id("debug-entry").all()
        ]
        if q.bundle and rec.bundle_id is not None:
            # CC turns carry no bundle, so these buttons are checked right after a
            # bundle turn, before the next turn can disable them.
            rec.page_downloads = {
                "json": _page_download(page, "json-download", downloads),
                "metadata": _page_download(page, "metadata-download", downloads),
            }
        page.keyboard.press("Escape")
        if q.cc_artifact:
            rec.page_artifacts = page.get_by_test_id("artifact-download").count()
        if rec.error or rec.status != "completed":
            break                            # later questions would only add noise

    yield records

    failed = _module_failures(request) > failed_before
    session_id = records[0].session_id if records else None
    kept = None
    if failed and session_id:
        kept = {"session_id": session_id,
                "debug_url": f"{base_url}/nextseek_api/nessie/sessions/{session_id}/debug/"}
        r = nessie_admin_api.get(f"{kept['debug_url']}?include=all", timeout=60)
        (nessie_evidence_dir / "debug.json").write_text(r.text)
    elif session_id:
        nessie_admin_api.delete(
            f"{base_url}/nextseek_api/assistant/sessions/{session_id}/", timeout=60)
    target = os.environ.get("CI_NESSIE_SUMMARY")
    if target:
        Path(target).write_text(json.dumps(
            summary_payload(records, nessie_budget, kept,
                            str(nessie_evidence_dir) if failed else None),
            indent=2))


def _rec(records: list, key: str) -> TurnRecord:
    for rec in records:
        if rec.key == key:
            return rec
    pytest.fail(f"{key} was never asked: an earlier question failed, see its test")
```

Note: the summary is written only when turns ran. When `--nessie-no-turns` skips `chat_run`, no summary is written and the CI record has no Nessie section.

- [ ] **Step 2: The per-question and cross-check tests** (all carry `nessie_turn`)

```python
turn = pytest.mark.nessie_turn
BUNDLE_QUESTIONS = [q for q in QUESTIONS if q.bundle]
CC_QUESTION = next(q for q in QUESTIONS if q.cc_artifact)


@turn
@pytest.mark.parametrize("q", QUESTIONS, ids=lambda q: q.key)
def test_each_question_completes_on_its_engine_through_the_router(q, chat_run):
    rec = _rec(chat_run, q.key)
    assert rec.error is None, f"{q.key}: {rec.error}"
    assert rec.status == "completed", f"{q.key}: status {rec.status}"
    assert (rec.route, rec.source) == (q.route, "baml"), (
        f"{q.key}: routed to {rec.route} by {rec.source}; expected {q.route} by baml. "
        "A 'heuristic' source means the BAML router is not answering.")
    assert rec.reply.strip(), f"{q.key}: empty reply"


@turn
def test_every_turn_rendered_its_reply_and_its_route_entry(chat_run, nessie_page):
    bubbles = nessie_page.locator('[data-testid="message-bubble"][data-role="assistant"]')
    assert bubbles.count() >= len(chat_run)
    for i, rec in enumerate(chat_run):
        assert plain_prefix(rec.reply) in normalize(bubbles.nth(i).inner_text()), (
            f"{rec.key}: the page does not show the reply the API returned")
        assert rec.debug_agents.count(ROUTE_ENTRY_AGENT) >= i + 1, (
            f"{rec.key}: the Debug panel has no route entry for this turn")


@turn
def test_the_system_answer_registers_no_bundle(chat_run):
    assert _rec(chat_run, "capabilities").bundle_id is None


@turn
@pytest.mark.parametrize("q", BUNDLE_QUESTIONS, ids=lambda q: q.key)
def test_bundle_turns_download_and_took_the_expected_path(q, chat_run, nessie_admin_api, base_url):
    rec = _rec(chat_run, q.key)
    assert isinstance(rec.bundle_id, int), f"{q.key}: no bundle registered"
    root = f"{base_url}/nextseek_api/assistant/sessions/{rec.session_id}/bundles/{rec.bundle_id}/"
    r = nessie_admin_api.get(root, timeout=60)
    assert r.status_code == 200, f"bundle JSON: {r.status_code}"
    bundle = r.json()
    assert bundle_path(bundle.get("mode")) == q.path, (
        f"{q.key}: the bundle was built by the {bundle_path(bundle.get('mode'))} path "
        f"(mode {bundle.get('mode')!r}); expected {q.path}")
    if q.path == "api":
        assert "api_result_full" in bundle, "the API bundle lacks the full API result"
    meta = nessie_admin_api.get(f"{root}?part=metadata", timeout=60)
    assert meta.status_code == 200 and "omitted" in meta.json()
    xlsx = [nessie_admin_api.get(f"{root}artifacts/{key}/", timeout=120)
            for key in ("search_results", "all_tables")]
    assert any(x.status_code == 200 and "spreadsheet" in x.headers.get("Content-Type", "")
               and len(x.content) > 0 for x in xlsx), (
        f"{q.key}: neither search_results nor all_tables downloaded as xlsx: "
        f"{[x.status_code for x in xlsx]}")
    assert set(rec.page_downloads) == {"json", "metadata"}, (
        f"{q.key}: the page's JSON and Metadata downloads did not both work")


@turn
def test_the_cc_turn_has_a_model_artifacts_and_a_bounded_cost(chat_run, nessie_admin_api, base_url):
    rec = _rec(chat_run, CC_QUESTION.key)
    assert rec.model_id, "cc_turn_meta.model_id is null, so the proxy will answer 403"
    assert rec.cost_usd is not None and 0 < rec.cost_usd <= CC_TURN_CAP_USD, (
        f"reported CC cost {rec.cost_usd}")
    files = [a for a in (rec.result or {}).get("artifacts") or []
             if a.get("artifact_type") == "file" and not a["key"].endswith("artifacts.zip")]
    assert files, "the CC turn left no artifact"
    assert rec.page_artifacts >= 1, "the page rendered no artifact link for the CC turn"
    turn_id = files[0]["key"].split("/", 1)[0]
    root = f"{base_url}/nextseek_api/cc-assistant/artifacts/{rec.session_id}/download/"
    one = nessie_admin_api.get(root, params={"key": files[0]["key"]}, timeout=120)
    assert one.status_code == 200 and len(one.content) > 0, f"one file: {one.status_code}"
    zipped = nessie_admin_api.get(root, params={"key": "all", "turn_id": turn_id}, timeout=120)
    assert zipped.status_code == 200 and "zip" in zipped.headers.get("Content-Type", "")
    alias = nessie_admin_api.get(
        f"{base_url}/nextseek_api/nessie/sessions/{rec.session_id}/artifacts/",
        params={"key": files[0]["key"]}, timeout=120)
    assert alias.status_code == 200, f"nessie artifacts alias: {alias.status_code}"


@turn
def test_the_session_detail_matches_the_page(chat_run, nessie_admin_api, base_url):
    sid = chat_run[0].session_id
    assert {r.session_id for r in chat_run} == {sid}, "the questions did not share one chat"
    r = nessie_admin_api.get(f"{base_url}/nextseek_api/assistant/sessions/{sid}/",
                             params={"include": "turns"}, timeout=60)
    assert r.status_code == 200
    turns = r.json()["turns"]
    assert len(turns) == len(QUESTIONS), f"{len(turns)} turns, expected {len(QUESTIONS)}"
    for t, rec in zip(turns, chat_run):
        assert t["user_query"] == rec.text
        assert t["reply"].strip() == rec.reply.strip(), f"{rec.key}: reply differs"
        if rec.bundle_id is not None:
            assert t["bundle_id"] == rec.bundle_id


@turn
def test_the_debug_endpoint_reports_the_session_and_resolves_a_task(chat_run, nessie_admin_api, base_url):
    sid = chat_run[0].session_id
    r = nessie_admin_api.get(f"{base_url}/nextseek_api/nessie/sessions/{sid}/debug/",
                             params={"include": "transcripts"}, timeout=60)
    assert r.status_code == 200
    d = r.json()
    assert d["resolved_as"] == "session"
    assert len(d["turns"]) == len(QUESTIONS) and len(d["tasks"]) == len(QUESTIONS)
    assert [row["route"] for row in d["ledger"]] == [q.route for q in QUESTIONS]
    assert all(row["route_source"] == "baml" for row in d["ledger"]), d["ledger"]
    assert d["transcripts"], "no CC transcript recorded"
    assert d["files"], "no files listed"
    assert not d["warnings"], f"warnings: {d['warnings']}"
    t = nessie_admin_api.get(
        f"{base_url}/nextseek_api/nessie/sessions/{chat_run[-1].task_id}/debug/", timeout=60)
    assert t.status_code == 200 and t.json()["resolved_as"] == "task"
    transcript = d["transcripts"][0]
    got = nessie_admin_api.get(f"{base_url}{transcript['url']}", timeout=60)
    assert got.status_code == 200 and "ndjson" in got.headers.get("Content-Type", "")
    alias = nessie_admin_api.get(
        f"{base_url}/nextseek_api/nessie/sessions/{sid}/transcript/{transcript['turn_id']}/",
        params={"cc_session_id": transcript["cc_session_id"]}, timeout=60)
    assert alias.status_code == 200, f"nessie transcript alias: {alias.status_code}"


@turn
def test_the_reopened_chat_shows_every_turn(chat_run, nessie_page):
    sid = chat_run[0].session_id
    page = nessie_page
    page.reload(wait_until="domcontentloaded")
    page.locator(f'[data-testid="session-item"][data-session-id="{sid}"]').click()
    bubbles = page.locator('[data-testid="message-bubble"][data-role="assistant"]')
    bubbles.nth(len(QUESTIONS) - 1).wait_for(state="visible", timeout=60_000)
    assert bubbles.count() == len(QUESTIONS)
    _open_debug(page)
    assert page.get_by_test_id("debug-entry").count() > 0, "the Debug panel was not rebuilt"
    page.keyboard.press("Escape")


@turn
def test_spend_stayed_under_the_ceiling(chat_run, nessie_budget):
    assert nessie_budget.refused == 0, "the page tried to send more chat POSTs than questions"
    assert not nessie_budget.over_ceiling, (
        f"reported spend ${nessie_budget.spent_usd:.2f} is over ${SPEND_CEILING_USD:.2f}")
```

Before committing, confirm these field names against the code and adjust the tests together if any differs: `resolved_as` and `counts` in `nextseek_api/assistant/session_debug.py`; the `turns[]` fields in `nextseek_api/assistant/models_api.py` (`Turn`); the transcript `url`, `turn_id` and `cc_session_id` keys (session_debug.py, `transcripts`); the bundle's `mode` key in the bundle JSON download; the `artifacts[]` entries (`artifact_type`, `key`) in `NessieAI/cc/cc_engine.py`; and whether the progress `result` carries `reply`, `bundle_id`, `artifacts` and `total_cost_usd` (the CC turn in `NessieAI/cc/turn.py` and the NS path in `NessieAI/ns/turn.py`).

- [ ] **Step 3: Verify without spending**
  - No-stack smoke lane: green.
  - `pytest ci/smoke/test_nessie.py --collect-only -q`: every test collected (stage 1, each question, the cross-checks).
  - Stage 1 live with `--nessie-no-turns`: stage 1 as in Task 5; every `nessie_turn` test reported skipped with "chat turns skipped by --nessie-no-turns".
  - Read the whole module once against the spec's section 3.1 tables: every row has a test.

- [ ] **Step 4: Commit** `feat(ci): Nessie lane stages 2 and 3, the four questions and the sessions cross-check`.

---

### Task 7: Startup: run the lane after an app rebuild, check its prerequisites, record it

**Files:**
- Modify: `startup/ci/runner.py`, `startup/steps/validate.py`, `startup/cli.py`, `.gitignore`
- Test: `startup/tests/test_ci_runner.py`, `startup/tests/test_validate.py`, `startup/tests/test_cli_commands.py`

**Interfaces:**
- Consumes: the suite's `--no-nessie` option (Task 2); `CI_NESSIE_SUMMARY` and `CI_NESSIE_EVIDENCE_DIR` (Task 6).
- Produces: `runner.build_command(..., nessie: bool = True)`; `runner.run_ci(..., nessie: bool = True)`; `runner.nessie_summary_path(repo_root) -> Path`; `runner.nessie_evidence_path(repo_root) -> Path`; `runner.read_nessie_summary(repo_root) -> dict | None`; `runner.render_nessie_section(summary: dict) -> list[str]`; `runner.write_report(..., nessie_summary: dict | None = None)`; `validate.nessie_prerequisites(repo_root, env, compose_project_name) -> tuple[HealthResult, ...]`; CLI `--nessie/--no-nessie` on `rebuild` and `ci`.

- [ ] **Step 1: Write the failing runner tests** (append to `startup/tests/test_ci_runner.py`)

```python
def test_build_command_runs_the_nessie_lane_by_default(tmp_path):
    assert "--no-nessie" not in runner.build_command(tmp_path, _state(), wait_ready=False)


def test_build_command_passes_no_nessie_when_off(tmp_path):
    cmd = runner.build_command(tmp_path, _state(), wait_ready=False, nessie=False)
    assert cmd[-1] == "--no-nessie"


def test_run_ci_names_the_nessie_summary_and_evidence_paths(tmp_path, monkeypatch):
    seen = {}

    def fake_run(cmd, cwd, env):
        seen.update(env)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    runner.nessie_summary_path(tmp_path).parent.mkdir(parents=True)
    runner.nessie_summary_path(tmp_path).write_text("{}")      # a stale one
    runner.run_ci(tmp_path, _state(), wait_ready=False)
    assert seen["CI_NESSIE_SUMMARY"] == str(runner.nessie_summary_path(tmp_path))
    assert seen["CI_NESSIE_EVIDENCE_DIR"] == str(runner.nessie_evidence_path(tmp_path))
    assert not runner.nessie_summary_path(tmp_path).exists(), "a stale summary survived"


SUMMARY = {
    "questions": [
        {"key": "capabilities", "text": "What can you do?", "expected_route": "nextseek_query",
         "route": "nextseek_query", "source": "baml", "task_id": "t1", "session_id": "s",
         "status": "completed", "seconds": 31.5, "cost_usd": None, "error": None},
        {"key": "nhp_graph", "text": "Make me a graph of NHP species",
         "expected_route": "container_cc", "route": "container_cc", "source": "baml",
         "task_id": "t4", "session_id": "s", "status": "completed", "seconds": 88.0,
         "cost_usd": 0.24, "error": None},
    ],
    "posts": 2, "refused_posts": 0, "spent_usd": 0.24, "ceiling_usd": 1.0,
    "kept_session": {"session_id": "s", "debug_url": "http://127.0.0.1:8000/nextseek_api/nessie/sessions/s/debug/"},
    "evidence_dir": None,
}


def test_render_nessie_section():
    text = "\n".join(runner.render_nessie_section(SUMMARY))
    assert text.startswith("## Nessie")
    assert "| capabilities | nextseek_query | baml | 31.5 | unmeasured | completed |" in text
    assert "| nhp_graph | container_cc | baml | 88.0 | $0.24 | completed |" in text
    assert "$0.24 of $1.00" in text
    assert "/nessie/sessions/s/debug/" in text
    assert "\u2014" not in text


def test_write_report_includes_the_nessie_section_and_moves_the_evidence(tmp_path):
    runner.junit_path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    runner.junit_path(tmp_path).write_text(
        '<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0" time="1">'
        '<testcase classname="c" name="n" time="1"/></testsuite></testsuites>')
    evidence = runner.nessie_evidence_path(tmp_path)
    evidence.mkdir(parents=True)
    (evidence / "page.png").write_bytes(b"png")
    path = runner.write_report(tmp_path, label="run1", nessie_summary=dict(SUMMARY))
    text = path.read_text()
    assert "## Nessie" in text
    moved = runner.reports_dir(tmp_path) / "run1-nessie"
    assert (moved / "page.png").is_file() and not evidence.exists()
    assert str(moved) in text
```

Match the junit fixture to what `summarize_junit` accepts (read it; copy an existing test's junit text if there is one).

- [ ] **Step 2: Run** the startup lane. Expected: the new tests fail.

- [ ] **Step 3: Implement the runner** (`startup/ci/runner.py`)

```python
import json
import shutil

NESSIE_SUMMARY_NAME = ".ci-nessie-last.json"
NESSIE_EVIDENCE_DIRNAME = ".ci-nessie-evidence"


def nessie_summary_path(repo_root: Path) -> Path:
    """Where ci/smoke/test_nessie.py writes the lane's summary. Gitignored, one slot."""
    return repo_root / "startup" / NESSIE_SUMMARY_NAME


def nessie_evidence_path(repo_root: Path) -> Path:
    """Where the lane writes a failure's trace, screenshot and debug JSON."""
    return repo_root / "startup" / NESSIE_EVIDENCE_DIRNAME


def read_nessie_summary(repo_root: Path) -> dict | None:
    try:
        return json.loads(nessie_summary_path(repo_root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def render_nessie_section(summary: dict) -> list[str]:
    lines = ["## Nessie", "",
             "| question | route | source | seconds | cost | status |",
             "|---|---|---|---|---|---|"]
    for q in summary.get("questions") or []:
        cost = "unmeasured" if q.get("cost_usd") is None else f"${q['cost_usd']:.2f}"
        status = q.get("status") or "not run"
        if q.get("error"):
            status = f"{status}: {q['error']}"
        lines.append(f"| {q.get('key')} | {q.get('route') or '-'} | {q.get('source') or '-'} "
                     f"| {q.get('seconds') if q.get('seconds') is not None else '-'} "
                     f"| {cost} | {status} |")
    lines += ["",
              f"- **Reported spend:** ${summary.get('spent_usd', 0):.2f} of "
              f"${summary.get('ceiling_usd', 1):.2f}; NS turns are unmeasured"]
    kept = summary.get("kept_session")
    if kept:
        lines.append(f"- **Kept session:** `{kept['session_id']}`; debug: {kept['debug_url']}")
    if summary.get("evidence_dir"):
        lines.append(f"- **Evidence:** `{summary['evidence_dir']}`")
    return lines + [""]
```

In `build_command`, add the keyword `nessie: bool = True` and, last:

```python
    if not nessie:
        cmd.append("--no-nessie")
```

In `run_ci`, add the keyword `nessie: bool = True`, pass it to `build_command`, add to `env`:

```python
        "CI_NESSIE_SUMMARY": str(nessie_summary_path(repo_root)),
        "CI_NESSIE_EVIDENCE_DIR": str(nessie_evidence_path(repo_root)),
```

and next to the junit unlink:

```python
    nessie_summary_path(repo_root).unlink(missing_ok=True)
    shutil.rmtree(nessie_evidence_path(repo_root), ignore_errors=True)
```

In `write_report`, add the keyword `nessie_summary: dict | None = None`. After the label is settled and before the health section is rendered:

```python
    if nessie_summary is not None:
        evidence = nessie_evidence_path(repo_root)
        if evidence.is_dir() and any(evidence.iterdir()):
            dest = reports_dir(repo_root) / f"{_safe_name(label)}-nessie"
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.rmtree(dest, ignore_errors=True)
                shutil.move(str(evidence), str(dest))
                nessie_summary["evidence_dir"] = str(dest)
            except OSError:
                pass
```

and after the health section:

```python
    if nessie_summary:
        lines += render_nessie_section(nessie_summary)
```

- [ ] **Step 4: The prerequisites check** (`startup/steps/validate.py`), test first in `startup/tests/test_validate.py`:

```python
def test_nessie_prerequisites_fail_on_an_empty_proxy_token(tmp_path, monkeypatch):
    (tmp_path / "docker" / "bedrock-proxy").mkdir(parents=True)
    (tmp_path / "docker" / "bedrock-proxy" / "proxy-secret.env").write_text(
        "AWS_BEARER_TOKEN_BEDROCK=\nAWS_REGION=us-east-1\n")
    ok = validate.HealthResult(name="x", ok=True, detail="fine")
    monkeypatch.setattr(validate, "check_first_party_images", lambda *a, **k: ok)
    monkeypatch.setattr(validate, "check_cc_services", lambda *a, **k: ok)
    monkeypatch.setattr(validate, "check_cc_runner", lambda *a, **k: ok)
    results = validate.nessie_prerequisites(tmp_path, {}, "nextseek")
    token = results[0]
    assert token.name == "bedrock proxy token" and token.ok is False


def test_nessie_prerequisites_never_print_the_token(tmp_path, monkeypatch):
    (tmp_path / "docker" / "bedrock-proxy").mkdir(parents=True)
    (tmp_path / "docker" / "bedrock-proxy" / "proxy-secret.env").write_text(
        "AWS_BEARER_TOKEN_BEDROCK=sekrit-value\n")
    ok = validate.HealthResult(name="x", ok=True, detail="fine")
    monkeypatch.setattr(validate, "check_first_party_images", lambda *a, **k: ok)
    monkeypatch.setattr(validate, "check_cc_services", lambda *a, **k: ok)
    monkeypatch.setattr(validate, "check_cc_runner", lambda *a, **k: ok)
    results = validate.nessie_prerequisites(tmp_path, {}, "nextseek")
    assert all(r.ok for r in results)
    assert all("sekrit" not in r.detail for r in results)
```

Implementation (read `HealthResult` at the top of the file for its exact fields first):

```python
def nessie_prerequisites(
    repo_root: Path, env: dict[str, str], compose_project_name: str
) -> tuple[HealthResult, ...]:
    """What the Nessie lane needs before it can pass: a CC turn reaches Bedrock
    only through the proxy, with its token, from a runnable cc-agent image.

    The proxy token is advisory in stack health; for the Nessie lane an empty one
    is a failure (spec decision 6), so its warning is turned into a failure here.
    """
    token = check_proxy_token(repo_root)
    if token.warn:
        token = HealthResult(name=token.name, ok=False, detail=token.detail)
    return (
        token,
        check_first_party_images(compose_project_name),
        check_cc_services(repo_root, env),
        check_cc_runner(repo_root, env),
    )
```

- [ ] **Step 5: The CLI** (`startup/cli.py`). Tests first in `startup/tests/test_cli_commands.py`, following that file's CliRunner and monkeypatch patterns for `rebuild` and `ci`:
  - `ci` on a `local` box calls `runner.build_command` and `runner.run_ci` with `nessie=True`; `ci --no-nessie` with `nessie=False`; a box whose `ci_profile` is `prod` (or empty) with `nessie=False`.
  - `rebuild --component cc-agent` runs CI with `nessie=False`; a bare `rebuild` on a `local` box with `nessie=True`.
  - With the lane on and a failing `validate.nessie_prerequisites` result, `ci` exits 1, prints the failing check's name, and never calls `runner.run_ci`.
  - `write_report` receives the dict `runner.read_nessie_summary` returned.

Implementation:

```python
def _nessie_active(state, requested: bool) -> bool:
    """The Nessie lane runs only where writes and model spend are allowed."""
    return requested and (state.ci_profile or "prod") in ("local", "dev")


def _nessie_prerequisites_or_exit(state, *, after_rebuild: bool) -> None:
    results = validate.nessie_prerequisites(REPO_ROOT, state.compose_env(),
                                            state.compose_project_name)
    failing = [r for r in results if not r.ok]
    for r in results:
        (ui.ok if r.ok else ui.fail)(f"nessie prerequisite, {r.name}: {r.detail}")
    if failing:
        prefix = "The rebuild itself succeeded, but the " if after_rebuild else "The "
        ui.fail(f"{prefix}Nessie lane cannot run: "
                + "; ".join(f"{r.name}: {r.detail}" for r in failing)
                + ". Fix it, or pass --no-nessie.")
        raise typer.Exit(code=1)
```

- `rebuild`: add the option

```python
    nessie: bool = typer.Option(
        True, "--nessie/--no-nessie",
        help="Include the Nessie lane (three NS questions and one CC question, about "
             "$0.30) in the post-rebuild CI. App rebuilds on local and dev only.",
    ),
```

  and in the CI branch, before `_ci_banner`: `nessie_on = _nessie_active(state, nessie) and _is_app_rebuild(policy)`, then `if nessie_on: _nessie_prerequisites_or_exit(state, after_rebuild=True)`; pass `nessie=nessie_on` to `build_command` and `run_ci`; pass `nessie_summary=runner.read_nessie_summary(REPO_ROOT) if nessie_on else None` to `write_report`. Define `_is_app_rebuild(policy) -> bool` after reading `startup/lib/rebuild_policy.py` for how the app component is named on the returned policy (a bare `rebuild` and `--component app` must both be true; `cc-agent`, `bedrock-proxy`, `nextseek-sidecar` and `custom-stack` false). Pin it with a test.
- `ci`: add the same option (help: "Include the Nessie lane (local and dev only)."), `nessie_on = _nessie_active(state, nessie)`, the prerequisites check with `after_rebuild=False` after stack health, and the same `nessie=` and `nessie_summary=` plumbing.

`.gitignore`: add `startup/.ci-nessie-last.json` and `startup/.ci-nessie-evidence/` next to the existing `startup/.ci-last-run.xml` or `startup/ci-reports/` rules (check which exist; `git check-ignore -v` both paths afterwards).

- [ ] **Step 6: Run** the startup lane (all green) and the no-stack smoke lane (still green).

- [ ] **Step 7: Commit** `feat(startup): run the Nessie lane after an app rebuild on local and dev, and record it`.

---

### Task 8: The dispatch workflow input, and the docs

**Files:**
- Modify: `.github/workflows/ci-smoke.yml`, `ci/smoke/README.md`, `ci/README.md`, `ci/CLAUDE.md`, `DEPLOYMENT.md`

- [ ] **Step 1: `ci-smoke.yml`.** Add under `workflow_dispatch.inputs`:

```yaml
      nessie:
        description: "Run the Nessie lane (three NS questions and one CC question, about $0.30)"
        type: boolean
        default: true
```

  and append `${{ inputs.nessie && '' || '--no-nessie' }}` to the `pytest ci/smoke/` command in the main (non-write) step. Leave the write step alone. Keep the file valid YAML (`python3 -c "import yaml,sys;yaml.safe_load(open('.github/workflows/ci-smoke.yml'))"` if PyYAML is on the host; otherwise check indentation by reading it back).

- [ ] **Step 2: `ci/smoke/README.md`: a "Nessie lane" section** after the "Tiers" section, with these parts, in plain words:
  - What it proves (the spec's goal sentence) and what it does not (answer accuracy: `NessieAI/tests/nessie_tests/`).
  - When it runs: after `./startup.sh rebuild` of the app and on `./startup.sh ci`, on `local` and `dev`; never `prod`; `--no-nessie` skips it; component rebuilds skip it. Cost about $0.30 and about 4 to 5 minutes.
  - Prerequisites: `CI_WRITE_USER` is a superuser in `ASSISTANT_PARTICIPATING_PROJECTS` with a SEEK project; the Bedrock proxy token is filled; `cc-agent` image present; `bedrock-proxy` and `nextseek-sidecar` running. Startup checks these first and fails naming the missing one.
  - How to extend: a question is a row in `QUESTIONS`; a new endpoint is a `ci/routes.py` entry plus a check; `--nessie-no-turns` runs stage 1 only while you iterate.
  - How to read a failure: the CI record's Nessie section, the kept session's `/debug/` URL, and the evidence folder (`trace.zip`, `page.png`, `debug.json`); open a trace with `npx playwright show-trace <trace.zip>`.
  - Add `test_nessie_unit.py` to the no-stack file list and its command (and add the missing `test_terminal_unit.py` while there).
  - Add `--no-nessie` and `--nessie-no-turns` rows to the flags table.
- [ ] **Step 3: `ci/README.md`**: one short paragraph naming the lane and linking the section above. **`ci/CLAUDE.md`**: a landmine: "Never opt out of the Nessie lane with `-m`: any `-m` expression switches the write lane on. Use `--no-nessie`." **`DEPLOYMENT.md`**: in the CI prerequisites list, the two Nessie prerequisites (the write account's project membership; the proxy token) and the `--no-nessie` flag.
- [ ] **Step 4: Check** every new line for em-dashes (`grep -nP '\x{2014}'` over the changed files must print nothing new), personal paths and emails.
- [ ] **Step 5: Commit** `docs(ci): the Nessie lane` (and the workflow change in the same commit or a separate `ci(github): ...` commit).

---

### Task 9: Whole-branch verification and handoff

- [ ] **Step 1:** Run every lane from "Commands used throughout": the no-stack smoke lane, the startup lane, the gate lane, the frontend (vitest and the mock Playwright project), `pytest ci/smoke/test_nessie.py --collect-only -q`, and stage 1 live with `--nessie-no-turns`. Save each output under `<scratch dir>/`.
- [ ] **Step 2:** `git log --oneline origin/dev..HEAD`; `git diff --stat origin/dev..HEAD`; confirm nothing unexpected is staged or untracked, no secret-like file, no `node_modules`, no file over 2 MB.
- [ ] **Step 3:** Write `<scratch dir>/HANDOFF.md`: the commits; each lane's result; every deviation from this plan; which stage 1 live checks failed only because the running bundle predates Task 4; and the operator's live paid run, which happens after this branch is merged (via `dev`) into the NessieAI refactor branch and a rebuild: `./startup.sh rebuild` then read the CI record's Nessie section; or `./startup.sh ci`. Include the merge notes from the spec's section 8. No em-dashes.

---

## Self-review

- **Spec coverage.** §1 goal and §2 decisions 1 to 10: Tasks 3, 5, 6, 7 (decision 2: Task 7's gating; 3: `QUESTIONS`; 4: Task 6's page-then-API design; 5: `nessie_admin_api` and the admin login; 6: `_nessie_prerequisites_or_exit` and failing tests; 7: `ChatBudget` and the spend test; 8: `chat_run`'s teardown; 9: `test_bundle_turns_download_and_took_the_expected_path`; 10: the worktree). §3.1: Tasks 3, 5, 6. §3.2: Task 1. §3.3: Task 2. §3.4: Task 7 and Task 8 (workflow input). §3.5: Task 4. §3.6: Task 8. §4: constants in Task 3. §5: unit tests in Tasks 1 to 4 and 7; the live run in Task 9's handoff. §6: T0 unchanged (Task 5's reachability test); `--no-nessie` (Task 2); the write gate not over HTTP (no task). §8: Task 9's handoff.
- **Deliberate refinements of the spec, recorded here so the executor knows:** `data-agent` replaces the spec's `data-kind` (Task 4); a `--nessie-no-turns` development option, and a `nessie_turn` marker, let stage 1 run without spending (Tasks 2, 5, 6); the debug entry's `expect` becomes 404 because the lane now requests it with an unknown id (Task 1); the page's JSON and Metadata downloads are exercised right after each bundle turn, because a CC turn carries no bundle and would disable the buttons (Task 6).
- **Placeholders.** The confirm-against-code notes in Tasks 3, 5, 6 and 7 name the exact file and symbol to read and what to do on a mismatch; no step is left to invent.
- **Names.** `ChatBudget`, `TurnRecord`, `classify_request`, `summary_payload`, `nessie_skip_reason`, `login_storage_state`, `nessie_prerequisites`, `render_nessie_section`, `read_nessie_summary`, `nessie_summary_path`, `nessie_evidence_path`, `CI_NESSIE_SUMMARY`, `CI_NESSIE_EVIDENCE_DIR` are used identically in every task that mentions them.
