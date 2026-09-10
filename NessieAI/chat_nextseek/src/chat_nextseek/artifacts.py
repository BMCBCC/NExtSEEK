from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def guess_file_mime(filename: str) -> str:
    """Infer a file MIME type from its extension, defaulting to binary."""
    ext = Path(filename).suffix.lower()
    return {
        ".json": "application/json",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".csv": "text/csv",
        ".txt": "text/plain",
        ".tsv": "text/tab-separated-values",
    }.get(ext, "application/octet-stream")


def build_file_manifest_entry(
    key: str,
    label: str,
    path: str | Path | None,
    filename: str | None = None,
    mime: str | None = None,
    *,
    kind: str | None = None,
    bundle_id: int | None = None,
    step_id: int | None = None,
) -> dict[str, Any] | None:
    """Return a standard file-manifest entry when the path exists on disk."""
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    name = filename or p.name
    entry: dict[str, Any] = {
        "key": key,
        "label": label,
        "path": str(p),
        "filename": name,
        "mime": mime or guess_file_mime(name),
    }
    if kind:
        entry["kind"] = kind
    if bundle_id is not None:
        entry["bundle_id"] = bundle_id
    if step_id is not None:
        entry["step_id"] = step_id
    return entry


def _drop_none_values(value: dict[str, Any]) -> dict[str, Any]:
    """Keep metadata compact while preserving false/zero/empty-list values."""
    return {k: v for k, v in value.items() if v is not None}


def _payload_is_on_disk(path: str | Path | None) -> bool:
    """True when a durable copy of the payload really exists at ``path``."""
    if not path:
        return False
    try:
        return Path(path).is_file()
    except (OSError, ValueError):
        return False


def _slim_memory_payload(memory_payload, api_result_full, raw_result_path):
    """Drop the rows memory_payload shares with the file already on disk.

    ``memory_payload["data"]`` is the SAME list object as
    ``api_result_full["data"]`` (orchestrator.py:1302), so on a large search it
    was a third 13 MB copy of rows that were already written to
    api_result_bundle_<id>.json. Read it back with load_memory_payload().

    Identity, not shape, decides. A graph or planner turn builds its own payload
    (orchestrator.py:1780 stores ``{"rows": ..., "total": ...}``), which is a
    different object and is left completely alone.
    """
    if not isinstance(memory_payload, dict) or "data" not in memory_payload:
        return memory_payload
    if not _payload_is_on_disk(raw_result_path):
        return memory_payload
    rows = api_result_full.get("data") if isinstance(api_result_full, dict) else None
    if memory_payload["data"] is not rows:
        return memory_payload
    return {k: v for k, v in memory_payload.items() if k != "data"}


def load_memory_payload(bundle: Any) -> dict[str, Any] | None:
    """A bundle's memory payload with its rows put back.

    Mirrors load_api_result_full: newer bundles omit ``data`` because the same
    rows are on disk, older ones carry it inline, and a pruned file simply
    leaves the key absent rather than raising.
    """
    if not isinstance(bundle, dict):
        return None
    payload = bundle.get("memory_payload")
    if not isinstance(payload, dict) or not payload:
        return payload
    if "data" in payload:
        return payload
    rows = load_api_result_full(bundle).get("data")
    return {**payload, "data": rows} if rows is not None else payload


def load_api_result_full(bundle: Any) -> dict[str, Any]:
    """The full API result for a bundle, wherever it happens to live.

    Bundles written before this stored the payload inline; bundles written now
    store only ``raw_result_path`` and leave the bytes on disk. Every in-process
    reader goes through here so both shapes work and neither has to care.

    Returns ``{}`` rather than raising when the file has been pruned: a reader
    that renders nothing is a much better outcome than a 500 on an old chat.
    """
    if not isinstance(bundle, dict):
        return {}

    inline = bundle.get("api_result_full")
    if inline:
        return inline if isinstance(inline, dict) else {}

    path = bundle.get("raw_result_path") or (bundle.get("paths") or {}).get("raw_result_path")
    if not path:
        return {}
    try:
        with open(path, "rb") as fh:
            loaded = json.load(fh)
    except (OSError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def build_metadata_bundle(
    *,
    bundle_id: int,
    mode: str,
    user_query: str,
    parser_plan: dict[str, Any] | None = None,
    api_plan: dict[str, Any] | None = None,
    api_result_full: dict[str, Any] | None = None,
    api_result_slim: dict[str, Any] | None = None,
    graph_plan: dict[str, Any] | None = None,
    graph_result: dict[str, Any] | None = None,
    reporter_plan: dict[str, Any] | None = None,
    reporter_result: dict[str, Any] | None = None,
    report_writer_output: dict[str, Any] | None = None,
    report_saved_files: dict[str, Any] | None = None,
    planner_output: dict[str, Any] | None = None,
    multi_parser_plan: dict[str, Any] | None = None,
    step_results: dict[Any, Any] | None = None,
    terminal_reply: str | None = None,
    provisional_reply: str | None = None,
    memory_payload: dict[str, Any] | None = None,
    search_context: dict[str, Any] | None = None,
    files: list[dict[str, Any]] | None = None,
    paths: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build the canonical session metadata bundle used by both standard and planner runs.

    The top-level aliases keep compatibility with existing memory/refine/evaluator
    code. The `model_outputs` block is the stable home for structured outputs from
    parser, planner, tool, reporter, graph, and chatter stages.
    """
    paths = paths or {}
    # The result payloads live at top level ONLY. They used to be stored here as
    # well, which doubled every bundle: on production a 13.5 MB search result
    # became a ~27 MB row and the write died with (2006, 'Server has gone away')
    # inside the background thread, losing a turn that had otherwise succeeded.
    # Nothing reads them back through this dict -- grepping the whole tree for
    # `model_outputs` finds only `memory_payload` (agents/memory.py:98) and
    # `terminal_reply`, which the orchestrator writes here itself -- so the
    # second copy was pure cost, worst at exactly the moment it mattered most.
    # The plans stay: they are small and this is their documented home.
    model_outputs = _drop_none_values(
        {
            "parser_plan": parser_plan,
            "api_plan": api_plan,
            "graph_plan": graph_plan,
            "reporter_plan": reporter_plan,
            "planner_output": planner_output,
            "multi_parser_plan": multi_parser_plan,
            "terminal_reply": terminal_reply,
            "provisional_reply": provisional_reply,
            # NOT memory_payload: it is 13 MB of API rows on a large search, and
            # both readers (agents/memory.py:41 and :98) take the top-level copy
            # first, so this one only ever cost the write. The :98 fallback is
            # kept for bundles written before this.
            "search_context": search_context,
        }
    )
    endpoint = None
    method = None
    request_body = {}
    query_params = {}
    if isinstance(api_plan, dict):
        endpoint = api_plan.get("endpoint")
        method = api_plan.get("method")
        request_body = api_plan.get("requestBody") or {}
        query_params = api_plan.get("queryParameters") or {}
    if isinstance(search_context, dict):
        endpoint = search_context.get("endpoint") or endpoint
        method = search_context.get("method") or method
        request_body = search_context.get("request_body") or request_body
        query_params = search_context.get("query_params") or query_params

    bundle = {
        "id": bundle_id,
        "timestamp": datetime.now().isoformat(),
        "user_query": user_query,
        "mode": mode,
        "model_outputs": model_outputs,
        "search_context": search_context or {},
        "terminal_reply": terminal_reply,
        "reply": terminal_reply,
        "provisional_reply": provisional_reply,
        "parser_plan": parser_plan,
        "api_plan": api_plan,
        "endpoint": endpoint,
        "method": method,
        "request_body": request_body,
        "query_params": query_params,
        # POINTER, NOT PAYLOAD. The full result is already written to disk as
        # api_result_bundle_<id>.json and its path recorded below as
        # raw_result_path, so storing it here too put a third copy of the same
        # bytes into MySQL -- results_history and last_debug are written by
        # session_adapter.save() in ONE update, and a 13.5 MB search became
        # ~40 MB of statement and died with (2006, 'Server has gone away'),
        # losing a turn that had already succeeded.
        #
        # Kept inline only when nothing on disk holds it (the artifact write
        # failed, or this path records no raw_result_path). Losing the result
        # outright would be far worse than a large row, so the fallback is to
        # behave exactly as before. Read it back with load_api_result_full().
        **({} if _payload_is_on_disk(paths.get("raw_result_path"))
           else {"api_result_full": api_result_full}),
        "memory_payload": _slim_memory_payload(
            memory_payload, api_result_full, paths.get("raw_result_path")
        ),
        "api_result_slim": api_result_slim,
        "raw_result_path": paths.get("raw_result_path"),
        "graph_plan": graph_plan,
        "graph_result": graph_result,
        "graph_debug_path": paths.get("graph_debug_path"),
        "reporter_plan": reporter_plan,
        "reporter_result": reporter_result,
        "report_writer_output": report_writer_output,
        "report_saved_files": report_saved_files or {},
        "plan": planner_output,
        "multi_parser_plan": multi_parser_plan,
        "step_results": step_results or {},
        "raw_result_paths": paths.get("raw_result_paths") or {},
        "graph_debug_paths": paths.get("graph_debug_paths") or {},
        "plan_debug_path": paths.get("plan_debug_path"),
        "paths": paths,
        "files": files or [],
    }
    if extra:
        bundle.update(extra)
    return bundle


class ArtifactStore:
    """Persist artifacts under a run log directory and emit standard manifest entries."""

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _artifact_dir(self, kind: str | None = None, subdir: str | None = None) -> Path:
        path = self.base_dir
        if kind:
            path = path / kind
        if subdir:
            path = path / subdir
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_json(
        self,
        *,
        key: str,
        label: str,
        filename: str,
        payload: Any,
        kind: str,
        subdir: str | None = None,
        bundle_id: int | None = None,
        step_id: int | None = None,
    ) -> dict[str, Any] | None:
        path = self._artifact_dir(kind, subdir) / filename
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return build_file_manifest_entry(
            key,
            label,
            path,
            kind=kind,
            bundle_id=bundle_id,
            step_id=step_id,
        )

    def write_text(
        self,
        *,
        key: str,
        label: str,
        filename: str,
        payload: str,
        kind: str,
        subdir: str | None = None,
        bundle_id: int | None = None,
        step_id: int | None = None,
        mime: str | None = None,
    ) -> dict[str, Any] | None:
        path = self._artifact_dir(kind, subdir) / filename
        path.write_text(payload, encoding="utf-8")
        return build_file_manifest_entry(
            key,
            label,
            path,
            mime=mime,
            kind=kind,
            bundle_id=bundle_id,
            step_id=step_id,
        )

    def write_bytes(
        self,
        *,
        key: str,
        label: str,
        filename: str,
        payload: bytes,
        kind: str,
        subdir: str | None = None,
        bundle_id: int | None = None,
        step_id: int | None = None,
        mime: str | None = None,
    ) -> dict[str, Any] | None:
        path = self._artifact_dir(kind, subdir) / filename
        path.write_bytes(payload)
        return build_file_manifest_entry(
            key,
            label,
            path,
            mime=mime,
            kind=kind,
            bundle_id=bundle_id,
            step_id=step_id,
        )

    def register_path(
        self,
        *,
        key: str,
        label: str,
        path: str | Path | None,
        kind: str,
        filename: str | None = None,
        mime: str | None = None,
        bundle_id: int | None = None,
        step_id: int | None = None,
    ) -> dict[str, Any] | None:
        return build_file_manifest_entry(
            key,
            label,
            path,
            filename=filename,
            mime=mime,
            kind=kind,
            bundle_id=bundle_id,
            step_id=step_id,
        )


def build_saved_report_file_manifest(
    saved_files: dict[str, Any] | None,
    *,
    key_prefix: str = "",
) -> list[dict[str, Any]]:
    """Normalize saved report artifacts into the standard file manifest."""
    reporter_file_labels: dict[str, str] = {
        "reporter_result": "Reporter result JSON",
        "samples_report": "Samples report JSON",
        "protocols_report": "Protocols report JSON",
        "published_report": "Published report JSON",
        "uuid_report_file": "UUID list",
        "merged_report": "Merged report JSON",
        "metadata": "Metadata JSON",
        "protocols": "Protocols JSON",
        "protocol_files": "Protocol files JSON",
        "geo_seq_workbooks": "GEO submission workbook",
        "sra_submission_workbooks": "SRA submission workbook",
        "sra_biosample_workbooks": "SRA BioSample workbook",
        "pride_submission_px": "PRIDE submission.px",
        "pride_sdrf": "PRIDE SDRF (experimental design)",
        "nfcore_csv_files": "nf-core CSV",
    }
    reporter_file_kinds: dict[str, str] = {
        "reporter_result": "report",
        "samples_report": "report",
        "protocols_report": "report",
        "published_report": "report",
        "uuid_report_file": "report",
        "merged_report": "report",
        "metadata": "report",
        "protocols": "protocol",
        "protocol_files": "protocol",
        "geo_seq_workbooks": "export",
        "sra_submission_workbooks": "export",
        "sra_biosample_workbooks": "export",
        "pride_submission_px": "export",
        "pride_sdrf": "export",
        "nfcore_csv_files": "export",
    }

    def _prefixed(key: str) -> str:
        return f"{key_prefix}{key}" if key_prefix else key

    result_files: list[dict[str, Any]] = []
    for key, path_value in (saved_files or {}).items():
        if isinstance(path_value, (list, tuple)):
            base_label = reporter_file_labels.get(key) or key.replace("_", " ")
            for i, item_path in enumerate(path_value):
                entry = build_file_manifest_entry(
                    _prefixed(f"{key}_{i}"),
                    f"{base_label} {i + 1}",
                    item_path,
                    kind=reporter_file_kinds.get(key, "report"),
                )
                if entry:
                    result_files.append(entry)
            continue

        label = reporter_file_labels.get(key) or (
            f"Report writer output ({key.replace('report_writer_output_', '')})"
            if key.startswith("report_writer_output_")
            else key
        )
        entry = build_file_manifest_entry(
            _prefixed(key),
            label,
            path_value,
            kind=reporter_file_kinds.get(
                key,
                "report_writer_output" if key.startswith("report_writer_output_") else "report",
            ),
        )
        if entry:
            result_files.append(entry)

    return result_files
