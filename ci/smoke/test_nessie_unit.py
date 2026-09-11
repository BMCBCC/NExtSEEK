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


from ci.smoke.test_nessie import (
    CHAT_PATH, MAX_CHAT_POSTS, QUESTIONS, SPEND_CEILING_USD, ChatBudget, TurnRecord,
    bundle_path, cc_model_id, classify_request, is_terminal, normalize, observed_path,
    plain_prefix, query_error, reported_cost, require_write_creds, route_decision,
    summary_payload,
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


def test_no_nessie_fixture_or_test_takes_the_skipping_write_creds_fixture():
    """conftest's write_creds skips when the account is missing (the opt-in write
    lane depends on that). Any Nessie function that requests it turns a missing
    account back into a green skip."""
    import ast
    import ci.smoke.test_nessie as nessie
    tree = ast.parse(Path(nessie.__file__).read_text())
    takers = sorted(
        node.name for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(a.arg == "write_creds"
                for a in node.args.posonlyargs + node.args.args + node.args.kwonlyargs)
    )
    assert takers == [], f"these request write_creds, which skips: {takers}"
