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


def test_the_plans_stay_in_model_outputs():
    """Plans are small and this is their documented home. memory_payload is NOT
    here: it is 13 MB of rows on a large search and both readers take the
    top-level copy first."""
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
                 "search_context", "terminal_reply"):
        assert kept in mo, f"{kept} must remain in model_outputs"
    assert "memory_payload" not in mo


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


# --- memory_payload is a THIRD copy of the same rows -------------------------
# Measured on production after the first fix shipped: results_history was still
# 26,190,151 bytes for one search, because memory_payload = {"data":
# api_result_full["data"], ...} (orchestrator.py:1302) and was ALSO duplicated
# into model_outputs. Both readers (agents/memory.py:41 and :98) prefer the
# top-level copy, so the model_outputs one never fires.

def test_memory_payload_is_not_duplicated_into_model_outputs():
    b = _bundle(memory_payload={"data": BIG["data"], "endpoint": "/x/"})

    assert "memory_payload" in b, "the copy both readers actually use"
    assert "memory_payload" not in b["model_outputs"]


def test_memory_payload_drops_the_rows_it_shares_with_the_file(tmp_path):
    """It holds the SAME list object as api_result_full, already on disk."""
    f = tmp_path / "r.json"
    f.write_text(json.dumps(BIG))
    rows = BIG["data"]

    b = _bundle(
        api_result_full={"data": rows},
        memory_payload={"data": rows, "endpoint": "/x/", "tool": "new_search"},
        paths={"raw_result_path": str(f)},
    )

    assert "data" not in b["memory_payload"], "the rows are on disk already"
    assert b["memory_payload"]["endpoint"] == "/x/", "the rest must survive"
    assert len(json.dumps(b, default=str)) < 5000


def test_a_memory_payload_that_is_not_the_api_rows_is_left_alone(tmp_path):
    """Graph and planner turns build their own payload. Identity, not shape, is
    what says 'these are the rows already written to that file'."""
    f = tmp_path / "r.json"
    f.write_text(json.dumps(BIG))

    b = _bundle(
        api_result_full={"data": BIG["data"]},
        memory_payload={"data": {"rows": [1, 2, 3], "total": 3}},
        paths={"raw_result_path": str(f)},
    )

    assert b["memory_payload"]["data"] == {"rows": [1, 2, 3], "total": 3}


def test_the_accessor_puts_the_rows_back(tmp_path):
    from chat_nextseek.artifacts import load_memory_payload

    f = tmp_path / "r.json"
    f.write_text(json.dumps(BIG))
    b = {"memory_payload": {"endpoint": "/x/"}, "raw_result_path": str(f)}

    assert load_memory_payload(b)["data"] == BIG["data"]


def test_the_accessor_leaves_an_intact_payload_untouched():
    from chat_nextseek.artifacts import load_memory_payload

    b = {"memory_payload": {"data": [1, 2], "endpoint": "/x/"}}

    assert load_memory_payload(b)["data"] == [1, 2]


def test_the_accessor_survives_a_bundle_with_no_memory_payload():
    from chat_nextseek.artifacts import load_memory_payload

    assert load_memory_payload({}) is None
    assert load_memory_payload({"memory_payload": {}}) in (None, {})
