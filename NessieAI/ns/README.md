# NessieAI/ns/

The engine half of the old `nextseek_api/assistant/`: the native granular ops that the
`ns-sidecar` and the CC agent call, their write gate, and projections of NS result bundles.
No Django models live here; the HTTP contract and the ORM stay in `nextseek_api/assistant/`.

## Surface

| Module | What it does |
|---|---|
| `granular.py` | `run_op` dispatches a table of nine handlers: seven ported sidecar ops, plus `run-ls` and `build-upload-xlsx` for reingest. Every `chat_nextseek` agent is imported inside a handler body |
| `write_gate.py` + `read_safe_endpoints.json` | `build_gate`: strict `True` confirms `api-write`; allowlist membership for `api-read`; pass for the read-class labels; deny anything else. The JSON is found beside the module |
| `reingest_qa.py` | `qa_rows` grades composed rows CLEAN, SOFT_FLAG or HARD_REJECT |
| `upload_workbook.py` | `render_upload_workbook` emits the four sheets the batch-upload parser reads |
| `bundle_download.py` | serves the files of a stored NS bundle |
| `debug_projection.py` | `bundle_debug_entries` rebuilds the Search Details panel from a stored bundle |

The HTTP contract for these ops (op table, request and response models, auth, error envelope) is
`nextseek_api/assistant/CONTRACT.md`. The ViewSet actions that call `run_op` are in
`nextseek_api/services/assistant.py`.

## Running and testing

Tests are in `NessieAI/tests/ns/` (engine) and `NessieAI/tests/api/` (HTTP surface); commands are in `NessieAI/tests/README.md`.

## Depends on / depended on by

- Depends on `NessieAI/chat_nextseek/` (agents, lazily) and `nextseek_api.batch_upload.helpers` (from `reingest_qa.py`, an allowed back-edge).
- Called by `nextseek_api/services/assistant.py`; `nextseek_api/assistant/session_debug.py` imports `bundle_download`.
- `NessieAI/cc/op_registry/ops.py` reads `read_safe_endpoints.json` at import.
- `NessieAI/docker/ns-sidecar/` calls these ops over HTTP and keeps its own copy of the wire models.
