# Operations

## Env vars

| Var | Required | Purpose |
|---|---|---|
| `NEXTSEEK_BASE_URL` / `API_USER` / `API_PASS` | yes | NExtSEEK REST API |
| `CATALOG_FILE` (or `AGENT_MODEL_CATALOG`) | yes | Agent model catalog; config construction raises without it |
| `GCP_API_KEY` (or the key of the provider `--mode` selects) | yes | LLM provider |
| `CHAT_NEXTSEEK_SKIP_BAML_BOOTSTRAP=1` | yes, in this repo | Skip the BAML regeneration attempt, which cannot succeed here (below) |
| `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` | optional | Enables graph-mode evaluation |

<a id="baml-regeneration"></a>
## BAML regeneration

On CLI entry the evaluator tries to regenerate `src/baml_client/` when it is
missing or older than any `.baml` source file. **In this repo that attempt fails**:
the generator block pins `version "0.221.0"` while the installed `baml-py`
resolves to 0.222.0, so `baml-cli generate` refuses, and running the same command
by hand fails the same way:

```bash
uv run baml-cli generate --from src/chat_nextseek/evaluator/baml_src
```

Set `CHAT_NEXTSEEK_SKIP_BAML_BOOTSTRAP=1` to skip the attempt. Batches then run and
write their artifacts, but a judgment on any supported path needs a generated client
or a double passed to the workflow; the evidence is the second landmine in
[../README.md](../README.md).

### When to regenerate manually

- Only after the generator pin and the installed `baml-py` agree again. Until then
  the command above is the one that fails.
- CI never regenerates this client: its one generation step targets the router's
  schema in `NessieAI/dmac_assistant/baml_src`.

## Failure buckets

| Bucket | Precedence | Meaning |
|---|---|---|
| `queries_exceptions` | 1 (highest) | Uncaught exception in the runner for this query. |
| `infra_failures` | 2 | Environment/provider fault caught and recorded structurally: Neo4j unreachable, 5xx after retries, missing env var. |
| `queries_with_errors` | 3 | Per-query error caught and recorded without becoming an exception bucket. |
| `queries_unsupported` | 4 | Parser returned `unsupported`, or judgment flagged the prompt as unsupported. |
| `queries_failed` | 5 | Final verdict `FAIL` or `PARTIAL`, including unresolved `RETRY` rows that never produced a passing retry outcome. |
| `queries_retried` | 6 | First attempt != PASS, retry returned PASS. |
| `queries_passed` | 7 | PASS on first attempt. |

`run_status`: `crashed` if any `queries_exceptions`; else `completed_with_failures`
if any of {failed, unsupported, with_errors, infra}; else `completed`.

## Troubleshooting

- **`RuntimeError: baml-cli generate failed`**: the version mismatch above, unless
  you changed a `.baml` file, in which case check stderr for a syntax error. Set
  `CHAT_NEXTSEEK_SKIP_BAML_BOOTSTRAP=1`.
- **`ModuleNotFoundError: No module named 'baml_client'`**: the client was never
  generated, which is the normal state in this repo. Only the judgment path needs it.
- **Neo4j-related infra_failures**: verify `NEO4J_URI` is reachable before rerunning.
- **Stale dashboard numbers after a classifier change**: rerun the batch.
  Classifier updates do not rewrite past reports.
