"""A bundle must not carry its heavy result payloads twice.

``build_metadata_bundle`` stored every result payload both inside
``model_outputs`` and again at top level. On production that doubled a 13.5 MB
search result into a ~27 MB row, and the MySQL write died with
(2006, 'Server has gone away') in a background thread, losing the whole turn:
session c0062000 finished successfully at 63.83s and persisted nothing.

Only two keys are ever read back out of ``model_outputs`` anywhere in the tree
(``memory_payload`` in agents/memory.py:98 and ``terminal_reply``, which the
orchestrator writes there itself), so the duplicated result payloads are dead
weight that is expensive precisely when a turn matters most.
"""

import json

from chat_nextseek.artifacts import build_metadata_bundle


BIG = {"data": [{"uid": f"NHP-{i}", "blob": "x" * 200} for i in range(500)]}


def _bundle(**kw):
    return build_metadata_bundle(
        bundle_id=1, mode="new_search", user_query="all the monkeys", **kw
    )


def test_the_heavy_result_payloads_are_not_stored_twice():
    b = _bundle(
        api_result_full=BIG,
        api_result_slim={"data": [{"uid": "NHP-1"}]},
        graph_result={"data": [{"n": 1}]},
        reporter_result={"rows_returned": 704},
        report_writer_output={"report": {}},
        step_results={"1": {"rows": 704}},
    )

    for heavy in ("api_result_full", "api_result_slim", "graph_result",
                  "reporter_result", "report_writer_output", "step_results"):
        assert heavy in b, f"{heavy} must stay at top level: that copy has readers"
        assert heavy not in b["model_outputs"], f"{heavy} is duplicated in model_outputs"


def test_the_plans_and_the_two_read_keys_stay_in_model_outputs():
    """Plans are small, and these are the only keys anything reads back."""
    b = _bundle(
        parser_plan={"mode": "new_search"},
        api_plan={"endpoint": "/x/"},
        graph_plan={"cypher": "MATCH (n) RETURN n"},
        reporter_plan={"summary_mode": "RPPR"},
        memory_payload={"recalled": []},
        search_context={"endpoint": "/x/"},
        terminal_reply="704 records.",
    )

    mo = b["model_outputs"]
    for kept in ("parser_plan", "api_plan", "graph_plan", "reporter_plan",
                 "memory_payload", "search_context", "terminal_reply"):
        assert kept in mo, f"{kept} must remain in model_outputs"


def test_dropping_the_duplicate_roughly_halves_a_large_bundle():
    b = _bundle(api_result_full=BIG)

    size = len(json.dumps(b, default=str))
    payload = len(json.dumps(BIG, default=str))

    # One copy, not two: the bundle carries the payload plus a little metadata.
    assert size < payload * 1.5, (
        f"bundle is {size:,} bytes for a {payload:,} byte payload; still duplicated"
    )
    assert size > payload, "the payload itself must still be there"


def test_a_bundle_with_no_results_is_unchanged_in_shape():
    b = _bundle(parser_plan={"mode": "system_question"})

    assert b["id"] == 1
    assert b["mode"] == "new_search"
    assert b["model_outputs"]["parser_plan"] == {"mode": "system_question"}


# --- the fourth copy: the DB should hold a pointer, not the payload -----------
# api_result_full is ALREADY written to disk as api_result_bundle_<id>.json and
# its path recorded as raw_result_path. Storing the payload inline as well meant
# results_history and last_debug each carried a second and third copy, and
# session_adapter.save() writes both columns in ONE UPDATE.

def test_the_payload_is_a_pointer_when_the_file_exists(tmp_path):
    f = tmp_path / "api_result_bundle_1.json"
    f.write_text(json.dumps(BIG))

    b = _bundle(api_result_full=BIG, paths={"raw_result_path": str(f)})

    assert "api_result_full" not in b, "the file exists; the DB must hold the pointer"
    assert b["raw_result_path"] == str(f)
    assert len(json.dumps(b, default=str)) < 5000, "bundle should now be tiny"


def test_the_payload_is_kept_inline_when_nothing_on_disk_holds_it(tmp_path):
    """Fail-safe: if the artifact write failed, losing the result outright would
    be far worse than a large row."""
    b = _bundle(api_result_full=BIG, paths={})

    assert b["api_result_full"] == BIG


def test_a_missing_file_does_not_silently_drop_the_payload(tmp_path):
    b = _bundle(api_result_full=BIG, paths={"raw_result_path": str(tmp_path / "gone.json")})

    assert b["api_result_full"] == BIG, "path recorded but no file: keep the payload"


# --- the accessor every in-process reader goes through -----------------------

def test_accessor_returns_the_inline_copy_for_an_old_bundle():
    from chat_nextseek.artifacts import load_api_result_full

    assert load_api_result_full({"api_result_full": BIG}) == BIG


def test_accessor_loads_from_disk_when_the_bundle_holds_only_a_pointer(tmp_path):
    from chat_nextseek.artifacts import load_api_result_full

    f = tmp_path / "r.json"
    f.write_text(json.dumps(BIG))

    assert load_api_result_full({"raw_result_path": str(f)}) == BIG


def test_accessor_degrades_to_empty_rather_than_raising(tmp_path):
    """Outputs get pruned. A reader must get {} and render nothing, not 500."""
    from chat_nextseek.artifacts import load_api_result_full

    assert load_api_result_full({"raw_result_path": str(tmp_path / "gone.json")}) == {}
    assert load_api_result_full({}) == {}
    assert load_api_result_full(None) == {}
