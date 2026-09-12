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


class _Config:
    """What pytest_collection_modifyitems reads from a config: three options and
    the memoised profile (set, so resolve_profile reads no environment)."""

    def __init__(self, *, m: str = "", no_nessie: bool = False, no_turns: bool = False):
        self._nextseek_profile = "local"
        self._options = {"-m": m, "--no-nessie": no_nessie, "--nessie-no-turns": no_turns}

    def getoption(self, name):
        return self._options[name]


class _Item:
    def __init__(self, *keywords: str):
        self.keywords = dict.fromkeys(keywords, True)
        self.skip_reasons: list[str] = []

    def get_closest_marker(self, name):
        return None                       # no profiles marker: the profile gate passes

    def add_marker(self, mark):
        assert mark.name == "skip", mark
        self.skip_reasons.append(mark.kwargs["reason"])


WRITE_SKIP = "write lane is opt-in: run with -m write"
NESSIE_SKIP = "Nessie lane skipped by --no-nessie"


def _collect(config: _Config) -> dict[str, list[str]]:
    from ci.smoke.conftest import pytest_collection_modifyitems
    items = {"write": _Item("write"), "nessie": _Item("nessie"),
             "turn": _Item("nessie", "nessie_turn"), "plain": _Item("test_x")}
    pytest_collection_modifyitems(config, list(items.values()))
    return {name: item.skip_reasons for name, item in items.items()}


def test_no_nessie_skips_the_lane_and_keeps_the_write_lane_deselected():
    """Spec 5: --no-nessie selection, including that the write lane stays out."""
    got = _collect(_Config(no_nessie=True))
    assert got["write"] == [WRITE_SKIP], got
    assert got["nessie"] == [NESSIE_SKIP], got
    assert got["turn"] == [NESSIE_SKIP], got
    assert got["plain"] == [], got


def test_nessie_no_turns_skips_only_the_turns_and_keeps_the_write_lane_deselected():
    got = _collect(_Config(no_turns=True))
    assert got["write"] == [WRITE_SKIP], got
    assert got["nessie"] == [], got
    assert got["turn"] == ["chat turns skipped by --nessie-no-turns"], got


def test_a_mark_expression_re_admits_the_write_lane_and_the_nessie_switch_still_holds():
    """The landmine in ci/CLAUDE.md, pinned: any -m (here the tempting
    "not nessie") leaves the write item unskipped, so the superuser write lane
    runs. --no-nessie is applied before that early return and still skips."""
    got = _collect(_Config(m="not nessie", no_nessie=True))
    assert got["write"] == [], got
    assert got["nessie"] == [NESSIE_SKIP], got
    assert got["turn"] == [NESSIE_SKIP], got


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


import json

from ci.smoke.test_nessie import (
    CHAT_PATH, MAX_CHAT_POSTS, QUESTIONS, SPEND_CEILING_USD, ChatBudget, TurnRecord,
    bundle_path, cc_model_id, classify_request, finish_chat, is_terminal, normalize,
    observed_path, offered_spreadsheets, plain_prefix, query_error, reported_cost,
    require_smoke_creds,
    require_write_creds, route_decision, summary_payload,
)

# pytester runs the lane's real chat_run fixture in a throwaway session, to pin
# which failures keep the chat (the cleanup tests at the end of this file).
pytest_plugins = ["pytester"]

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


def test_bundle_path_names_an_unexpected_mode_instead_of_calling_it_api():
    """Only the two search modes are the API path (search_results answers only
    them, services/assistant.py). Any other mode is reported under its own name,
    so a flip to reporter or a submission fails the path check saying which."""
    assert bundle_path("graph_query") == "graph"
    assert bundle_path("new_search") == "api"
    assert bundle_path("refine_last_search") == "api"
    assert bundle_path("reporter") == "reporter"
    assert bundle_path("generate_submission") == "generate_submission"
    assert bundle_path("") == "no mode"
    assert bundle_path(None) == "no mode"


def _parametrized_rows(test_function) -> list:
    marks = [m for m in getattr(test_function, "pytestmark", []) if m.name == "parametrize"]
    assert len(marks) == 1, f"{test_function.__name__} is not parametrized once: {marks}"
    return list(marks[0].args[1])


@pytest.mark.parametrize("test_name, kind", [
    ("test_each_question_completes_on_its_engine_through_the_router", lambda q: True),
    ("test_each_system_answer_registers_no_bundle", lambda q: q.path == "system"),
    ("test_bundle_turns_download_and_took_the_expected_path", lambda q: q.bundle),
    ("test_each_cc_turn_has_a_model_artifacts_and_a_bounded_cost",
     lambda q: q.route == "container_cc"),
], ids=lambda v: v if isinstance(v, str) else "")
def test_every_per_question_check_covers_every_row_of_its_kind(test_name, kind):
    """"A new question is a new row" (spec 3.1): each per-question check is
    parametrized over every row it applies to, never tied to one key or to the
    first match, so a second system or CC row gets every check too."""
    import ci.smoke.test_nessie as nessie
    assert hasattr(nessie, test_name), f"{test_name} is not in test_nessie.py"
    got = [q.key for q in _parametrized_rows(getattr(nessie, test_name))]
    assert got == [q.key for q in QUESTIONS if kind(q)], f"{test_name} covers {got}"


def test_observed_path_of_a_turn_without_a_bundle():
    """The CI record's path column. A CC turn took the cc path; an NS turn that
    registered no bundle took the system path (the system agent ends with
    bundle_id=None); a bundle turn's path is its bundle's mode, which the bundle
    test reads, so it is not guessed here."""
    assert observed_path("container_cc", None) == "cc"
    assert observed_path("nextseek_query", None) == "system"
    assert observed_path("nextseek_query", 7) is None
    assert observed_path(None, None) is None


def test_reply_matching_survives_markdown():
    reply = "**NDMA-treated mice**: 12 found\n\n| id | sex |"
    assert plain_prefix(reply) == "ndma treated mice 12 found"
    assert plain_prefix(reply) in normalize("NDMA-treated mice: 12 found  | id | sex |")
    assert plain_prefix("") == ""


def test_summary_payload_shape():
    rec = TurnRecord(key="nhp_graph", text="t", expected_route="container_cc",
                     route="container_cc", source="baml", task_id="a", session_id="s",
                     status="completed", seconds=88.0, cost_usd=0.24, path="cc")
    b = ChatBudget()
    b.admit_post()
    b.add_cost(0.24)
    out = summary_payload([rec], b, None, "/tmp/e")
    assert out["posts"] == 1 and out["spent_usd"] == 0.24 and out["ceiling_usd"] == 1.0
    assert out["questions"][0]["key"] == "nhp_graph"
    assert out["questions"][0]["expected_route"] == "container_cc"
    # Spec 3.4: the record names the path each question took.
    assert out["questions"][0]["path"] == "cc"
    assert out["kept_session"] is None and out["evidence_dir"] == "/tmp/e"


def test_missing_write_credentials_fail_the_lane_and_never_skip(monkeypatch, tmp_path):
    """Decision 6: a misconfigured box fails and names the cause. A skip would let
    the whole lane read green on a box whose ci.env has no write account."""
    monkeypatch.delenv("CI_WRITE_USER", raising=False)
    monkeypatch.delenv("CI_WRITE_PASS", raising=False)
    monkeypatch.setenv("NEXTSEEK_CI_ENV", str(tmp_path / "absent.env"))
    # Skipped is not a subclass of Failed, so pytest.raises(pytest.fail.Exception)
    # would let a skip escape and report this pin itself as skipped: green again.
    try:
        require_write_creds()
    except pytest.skip.Exception:
        pytest.fail("require_write_creds skipped; a missing write account must fail "
                    "the lane, never skip it")
    except pytest.fail.Exception as failed:
        message = str(failed)
    else:
        pytest.fail("require_write_creds returned with no credentials set anywhere")
    for name in ("CI_WRITE_USER", "CI_WRITE_PASS", "ci.env"):
        assert name in message, f"the failure does not name {name}: {message}"


def test_write_credentials_come_from_the_environment_or_the_file(monkeypatch, tmp_path):
    monkeypatch.delenv("CI_WRITE_USER", raising=False)
    monkeypatch.delenv("CI_WRITE_PASS", raising=False)
    env_file = tmp_path / "ci.env"
    env_file.write_text("CI_WRITE_USER=file-user\nCI_WRITE_PASS=file-pass\n")
    monkeypatch.setenv("NEXTSEEK_CI_ENV", str(env_file))
    assert require_write_creds() == ("file-user", "file-pass")
    monkeypatch.setenv("CI_WRITE_USER", "env-user")
    monkeypatch.setenv("CI_WRITE_PASS", "env-pass")
    assert require_write_creds() == ("env-user", "env-pass")


def test_missing_smoke_credentials_fail_the_lane_and_never_skip(monkeypatch, tmp_path):
    """Decision 6 again: without the smoke account the smoke-auth and web-auth checks
    would skip, and the lane would exit green on a misconfigured box."""
    monkeypatch.delenv("CI_SMOKE_USER", raising=False)
    monkeypatch.delenv("CI_SMOKE_PASS", raising=False)
    monkeypatch.setenv("NEXTSEEK_CI_ENV", str(tmp_path / "absent.env"))
    # Caught explicitly for the reason the write-credentials pin gives: a skip is
    # not a failure, and would report this pin itself as skipped.
    try:
        require_smoke_creds()
    except pytest.skip.Exception:
        pytest.fail("require_smoke_creds skipped; a missing smoke account must fail "
                    "the lane, never skip it")
    except pytest.fail.Exception as failed:
        message = str(failed)
    else:
        pytest.fail("require_smoke_creds returned with no credentials set anywhere")
    for name in ("CI_SMOKE_USER", "CI_SMOKE_PASS", "ci.env"):
        assert name in message, f"the failure does not name {name}: {message}"


def test_smoke_credentials_come_from_the_environment_or_the_file(monkeypatch, tmp_path):
    monkeypatch.delenv("CI_SMOKE_USER", raising=False)
    monkeypatch.delenv("CI_SMOKE_PASS", raising=False)
    env_file = tmp_path / "ci.env"
    env_file.write_text("CI_SMOKE_USER=file-user\nCI_SMOKE_PASS=file-pass\n")
    monkeypatch.setenv("NEXTSEEK_CI_ENV", str(env_file))
    assert require_smoke_creds() == ("file-user", "file-pass")
    monkeypatch.setenv("CI_SMOKE_USER", "env-user")
    monkeypatch.setenv("CI_SMOKE_PASS", "env-pass")
    assert require_smoke_creds() == ("env-user", "env-pass")


# conftest fixtures that skip when an account is missing: write_creds and
# smoke_creds themselves, and the clients and browser state built on smoke_creds.
SKIPPING_FIXTURES = frozenset({"write_creds", "smoke_creds", "api", "web",
                               "storage_state", "page"})


def test_no_nessie_fixture_or_test_takes_a_skipping_credentials_fixture():
    """The opt-in write lane and the general sweep rely on those fixtures skipping.
    Any Nessie test or fixture that requests one turns a missing account back into
    a green skip, which decision 6 rules out. Plain helpers (_poll, _ask) take
    clients by argument and are not fixtures, so only tests and fixtures count."""
    import ast
    import ci.smoke.test_nessie as nessie
    tree = ast.parse(Path(nessie.__file__).read_text())

    def is_fixture(node) -> bool:
        return any("fixture" in ast.unparse(d) for d in node.decorator_list)

    takers = sorted(
        f"{node.name}({arg.arg})"
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and (node.name.startswith("test_") or is_fixture(node))
        for arg in node.args.posonlyargs + node.args.args + node.args.kwonlyargs
        if arg.arg in SKIPPING_FIXTURES
    )
    assert takers == [], f"these request a fixture that skips: {takers}"


# --------------------------------------------------------------------------- #
# cleanup (spec 3.1, decision 8): delete the chat on a pass, keep it otherwise
# --------------------------------------------------------------------------- #

class _Answer:
    def __init__(self, status_code: int, text: str = ""):
        self.status_code, self.text = status_code, text


class _Api:
    def __init__(self, delete_answer: _Answer | None = None,
                 delete_raises: Exception | None = None):
        self.calls: list[tuple[str, str]] = []
        self._delete_answer = delete_answer or _Answer(204)
        self._delete_raises = delete_raises

    def get(self, url, **kw):
        self.calls.append(("GET", url))
        return _Answer(200, '{"resolved_as": "session"}')

    def delete(self, url, **kw):
        self.calls.append(("DELETE", url))
        if self._delete_raises is not None:
            raise self._delete_raises
        return self._delete_answer


def test_finish_chat_deletes_a_passing_lane_s_chat(tmp_path):
    api = _Api()
    assert finish_chat(api, BASE, "s1", failed=False, evidence_dir=tmp_path) == (None, None)
    assert api.calls == [("DELETE", f"{BASE}/nextseek_api/assistant/sessions/s1/")]
    assert not (tmp_path / "debug.json").exists()


@pytest.mark.parametrize("delete_answer, delete_raises, expected", [
    (_Answer(500, "server   error"), None, "DELETE answered 500: server error"),
    (_Answer(404), None, "DELETE answered 404"),
    (None, ConnectionError("refused"), "ConnectionError: refused"),
])
def test_finish_chat_reports_a_chat_it_could_not_delete(delete_answer, delete_raises,
                                                        expected, tmp_path):
    """A failed DELETE leaves the chat behind. It must say so, not pass in silence."""
    api = _Api(delete_answer=delete_answer, delete_raises=delete_raises)
    kept, error = finish_chat(api, BASE, "s1", failed=False, evidence_dir=tmp_path)
    assert kept is None
    assert error is not None, "a chat that was not deleted must be reported"
    assert "s1" in error, f"the report does not name the chat: {error}"
    assert expected in error, f"the report does not say why: {error}"


def test_finish_chat_keeps_a_failing_lane_s_chat_and_its_debug_answer(tmp_path):
    api = _Api()
    kept, error = finish_chat(api, BASE, "s1", failed=True, evidence_dir=tmp_path)
    assert error is None
    assert kept == {"session_id": "s1",
                    "debug_url": f"{BASE}/nextseek_api/nessie/sessions/s1/debug/"}
    assert [method for method, _ in api.calls] == ["GET"], (
        f"a failing lane must keep its chat: {api.calls}")
    assert (tmp_path / "debug.json").read_text() == '{"resolved_as": "session"}'


def test_finish_chat_with_no_chat_does_nothing(tmp_path):
    api = _Api()
    assert finish_chat(api, BASE, None, failed=True, evidence_dir=tmp_path) == (None, None)
    assert api.calls == []


def test_summary_payload_carries_the_cleanup_error():
    out = summary_payload([], ChatBudget(), None, None, cleanup_error="the chat s was not deleted")
    assert out["cleanup_error"] == "the chat s was not deleted"
    assert summary_payload([], ChatBudget(), None, None)["cleanup_error"] is None


# The lane's own chat_run fixture, run in a pytester session with a fake page and
# a fake API. Every other fixture it takes is the real one.
_LANE_CONFTEST = '''
def pytest_addoption(parser):
    parser.addoption("--nessie-no-turns", action="store_true")
'''

_LANE_MODULE = '''
import json
from types import SimpleNamespace

import pytest

from ci.smoke.test_nessie import chat_run, nessie_budget, nessie_failures_before

CALLS = {calls!r}


class Answer:
    def __init__(self, status_code, text=""):
        self.status_code, self.text = status_code, text


class Api:
    def get(self, url, **kw):
        self._log("GET", url)
        return Answer(200, "{{}}")

    def delete(self, url, **kw):
        self._log("DELETE", url)
        return Answer(204)

    def _log(self, method, url):
        with open(CALLS, "a") as f:
            f.write(json.dumps([method, url]) + "\\n")


@pytest.fixture(scope="module")
def nessie_admin_api():
    return Api()


@pytest.fixture(scope="module")
def base_url():
    return "http://stack"


@pytest.fixture(scope="module")
def nessie_evidence_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("evidence")


@pytest.fixture(scope="module")
def nessie_page():
    button = SimpleNamespace(click=lambda: None)
    return SimpleNamespace(get_by_test_id=lambda test_id: button)


def test_a_stage_1_check():
    assert {stage_1_passes}


def test_a_turn_check(chat_run):
    assert [r.status for r in chat_run] == ["completed"] * len(chat_run)
'''


def _fake_ask(page, q, rec, index, **_):
    rec.task_id, rec.session_id, rec.status = f"t{index}", "s1", "completed"


def _run_lane(pytester, monkeypatch, tmp_path, *, stage_1_passes: bool):
    """Run a stage 1 test and a turn test through the real chat_run; return the
    pytester result, the summary chat_run wrote and the HTTP methods it sent."""
    import ci.smoke.test_nessie as lane
    monkeypatch.setattr(lane, "_ask", _fake_ask)
    summary, calls = tmp_path / "summary.json", tmp_path / "calls.ndjson"
    monkeypatch.setenv("CI_NESSIE_SUMMARY", str(summary))
    pytester.makeconftest(_LANE_CONFTEST)
    pytester.makepyfile(test_lane=_LANE_MODULE.format(
        calls=str(calls), stage_1_passes=stage_1_passes))
    result = pytester.runpytest_inprocess("-p", "no:cacheprovider")
    methods = ([json.loads(line)[0] for line in calls.read_text().splitlines()]
               if calls.exists() else [])
    return result, json.loads(summary.read_text()), methods


def test_a_stage_1_failure_keeps_the_chat_even_when_every_turn_test_passes(
        pytester, monkeypatch, tmp_path):
    """Spec 3.1 and decision 8: the chat is deleted only when every test passed.
    A stage 1 failure runs before chat_run is first requested, so a failure
    count taken in chat_run's own setup would miss it and delete the chat."""
    result, summary, methods = _run_lane(pytester, monkeypatch, tmp_path,
                                         stage_1_passes=False)
    result.assert_outcomes(passed=1, failed=1)
    assert summary["kept_session"] is not None, f"the chat was not kept: {summary}"
    assert summary["kept_session"]["session_id"] == "s1"
    assert summary["evidence_dir"], f"a red lane names no evidence folder: {summary}"
    assert "DELETE" not in methods, f"a red lane deleted its chat: {methods}"


def test_a_green_lane_deletes_its_chat_and_reports_no_cleanup_error(
        pytester, monkeypatch, tmp_path):
    result, summary, methods = _run_lane(pytester, monkeypatch, tmp_path,
                                         stage_1_passes=True)
    result.assert_outcomes(passed=2)
    assert summary["kept_session"] is None, f"a green lane kept its chat: {summary}"
    assert summary["evidence_dir"] is None
    assert summary["cleanup_error"] is None
    assert methods == ["DELETE"], f"expected one DELETE, got {methods}"


def test_offered_spreadsheets_are_the_tables_and_xlsx_files_a_turn_offered():
    artifacts = [
        {"artifact_type": "file", "key": "api_result", "file_format": "json"},
        {"artifact_type": "table", "key": "samples", "label": "Samples"},
        {"artifact_type": "file", "key": "geo_seq_workbooks", "file_format": "xlsx"},
        {"artifact_type": "table"},                 # no key: nothing to download
        "not-a-dict",
    ]
    assert offered_spreadsheets(artifacts) == ["samples", "geo_seq_workbooks"]
    assert offered_spreadsheets(None) == []
    assert offered_spreadsheets([{"artifact_type": "file", "key": "api_result",
                                  "file_format": "json"}]) == [], (
        "a turn that offers only its JSON result must be asked for no spreadsheet")


def test_the_cc_cost_cap_is_a_rate_per_minute_with_a_one_minute_floor():
    """The CC turn's cost bound scales with how long the turn ran: $0.50 a
    minute, never below one minute's worth, so a longer turn is not failed for
    costing a little over a flat $0.50."""
    from ci.smoke.test_nessie import CC_COST_PER_MINUTE_USD, cc_turn_cap_usd
    assert CC_COST_PER_MINUTE_USD == 0.50
    assert cc_turn_cap_usd(None) == 0.50
    assert cc_turn_cap_usd(30.0) == 0.50
    assert cc_turn_cap_usd(60.0) == 0.50
    assert cc_turn_cap_usd(120.0) == 1.00
    assert 0.5400435 <= cc_turn_cap_usd(119.7)   # run 6's turn now passes
    assert not 0.51 <= cc_turn_cap_usd(30.0)     # a 30 s turn over $0.50 still fails
