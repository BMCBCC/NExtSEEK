"""Projections of a result bundle for the Debug Output panel's downloads.

The panel offers two buttons. "JSON" hands over the whole bundle; "Metadata"
hands over the provenance of the turn without the bulk result payloads, which
on production run to ~510 KB for a single search.

Both used to hit the same endpoint with ``?format=json`` / ``?format=metadata``.
``download_bundle`` never read ``format``, and ``format`` is DRF's own
content-negotiation parameter: with no renderer named "metadata", negotiation
raised 404 in ``APIView.initial()`` before the view body ran. The button had
therefore never worked anywhere. Selection moved to ``?part=``, a name DRF does
not own, so ``?format=json`` keeps meaning what DRF has always made it mean.
"""

from __future__ import annotations

import json
from typing import Any

#: What the turn *was*: the question, the routing, the plans, and pointers to
#: everything the run wrote. Deliberately an allowlist. Metadata is a curated
#: summary, so a heavy field added to the bundle later must stay out of it until
#: someone decides it belongs. (The opposite of the rule for file artifacts in
#: excel_export.py, where a new output kind going unseen was the defect itself.)
_METADATA_FIELDS: tuple[str, ...] = (
    "id",
    "timestamp",
    "user_query",
    "mode",
    "terminal_reply",
    "provisional_reply",
    "endpoint",
    "method",
    "request_body",
    "query_params",
    "search_context",
    "parser_plan",
    "api_plan",
    "graph_plan",
    "reporter_plan",
    "multi_parser_plan",
    "plan",
    "report_saved_files",
    "files",
    "paths",
    "raw_result_path",
    "raw_result_paths",
    "graph_debug_path",
    "graph_debug_paths",
    "plan_debug_path",
)

#: Result payloads the summary replaces with a size, not with silence.
_BULK_FIELDS: tuple[str, ...] = (
    "api_result_full",
    "api_result_slim",
    "graph_result",
    "reporter_result",
    "report_writer_output",
    "step_results",
    "model_outputs",
    "memory_payload",
)

_NOTE = (
    "Summary of one turn. Result payloads are listed under 'omitted' with "
    "their sizes; use the full bundle download to get them."
)


def _size(value: Any) -> int:
    """Serialized size of a payload, for telling the reader what it is missing."""
    try:
        return len(json.dumps(value, default=str))
    except (TypeError, ValueError):
        return 0


def bundle_metadata(bundle: dict[str, Any]) -> dict[str, Any]:
    """The provenance of a turn, without the result payloads.

    Keys absent from the bundle stay absent rather than appearing as nulls, so
    the file shows what the turn actually did and not a template of what a turn
    could do. ``omitted`` names every bulk payload that was dropped and how big
    it was, so the summary cannot quietly mislead about what it left behind.
    """
    if not isinstance(bundle, dict):
        return {"note": _NOTE, "omitted": {}}

    meta: dict[str, Any] = {
        key: bundle[key] for key in _METADATA_FIELDS if key in bundle
    }

    omitted: dict[str, Any] = {}
    for key in _BULK_FIELDS:
        if key not in bundle:
            continue
        value = bundle[key]
        if value in (None, {}, [], ""):
            continue
        entry: dict[str, Any] = {"bytes": _size(value)}
        if isinstance(value, dict):
            rows = value.get("data")
            if isinstance(rows, list):
                entry["rows"] = len(rows)
            if isinstance(value.get("rows_returned"), int):
                entry["rows_returned"] = value["rows_returned"]
        omitted[key] = entry

    meta["omitted"] = omitted
    meta["note"] = _NOTE
    return meta
