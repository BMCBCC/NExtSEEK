# Working in NessieAI/docker/

## Invariants

Each is enforced from outside this folder. Breaking one is a security regression, a silent deploy failure or a red suite.

- **Five `bedrock-proxy/` files are digest-pinned** (its Python modules and the secret-env example) inside `NessieAI/tests/cc/test_step7_proxy_port.py`. An in-place edit fails; updating the port manifest does not silence it.
- **Every `.py` under `ns-sidecar/` is digest-pinned** the same way, in `NessieAI/tests/cc/test_step7_sidecar_port.py`. Port, never rewrite.
- **`cc-runtime/PORT-EVIDENCE.json` is an enforced integrity manifest.** It records a size and digest per file and `NessieAI/tests/cc/test_step7_cc_runtime_port.py` asserts both. Change a catalog, an ingested doc or the baked capabilities, and update the manifest in the same commit.
- **The canonical capabilities `COPY` stays the last writer of its in-image path.** That block of `cc-runtime/Dockerfile` is generated, and `NessieAI/build_tools/gen_op_surfaces/docker_blocks.py` refuses a later writer.
- **The sidecar's staging hash and the Django sweep's are one function.** `ns-sidecar/app/staging.py` is the definition and `NessieAI/cc/cc_staging.py` re-implements it. Change one alone and staged artifacts land where the sweep never looks.
- **The proxy never publishes a host port.** It authenticates no caller and attaches the institutional token to every request it relays.
- **A client `Authorization` header is dropped, never forwarded** (the hop-by-hop drop set in `bedrock-proxy/app/proxy.py`).
- **The fd-shuffle in `cc-runtime/container/runner_ns.py` stays its first executable statement.**
- **`cc-runtime/container/CLAUDE.md` stays committed.** It is a required Dockerfile `COPY` input. Only its marked blocks (`PLAN005-GEN`, `NEXTSEEK-DOCS`) are generated; everything else is hand-written.
- **`cc-runtime/` holds no BAML sources.** Its Dockerfile COPYs the Compose named context `dmac_assistant_baml` (the canonical `NessieAI/dmac_assistant/baml_src/`) to `/app/baml_src/`; a copy added here is refused by `NessieAI/tests/router/test_baml_single_source.py`. A BAML edit therefore needs a cc-agent rebuild as well as the app rebuild.

## Landmines

- **The baked `capabilities.md` is not what the agent reads.** The named-context `COPY` overwrites it with the canonical bytes. Its drift from the canonical file is documented once, in `NessieAI/chat_nextseek/CLAUDE.md`; the fix touches `PORT-EVIDENCE.json` here.
- **Two other baked catalogs, `min_graph_schema.json` and `neo4j_schema.json`, differ from canonical and DO reach the agent.** Nothing overwrites them. The catalog snapshot generator lives in an external clone, so they are hand-maintained here, together with their digests.
- **A bare `pytest` inside `cc-runtime/` exits 1 even when every test passes**: the declared coverage targets name trees this port lacks. Pass `-o addopts=""`.
- **`docker build` on `cc-runtime/` alone fails.** The named contexts `chat_nextseek` and `dmac_assistant_baml` exist only through compose; a manual build must pass both as `--build-context`, exactly as the generated `additional_contexts` block in `docker-compose.yml` declares them.
- **The plugin `hooks/hooks.json` is inert in the image.** The container entrypoint re-registers the hook; edit that block.
- **`cc-runtime/container/runner_ns.py` ships but nothing calls it.** Do not read it as how a turn runs.
- **`cc-runtime/build_context/docs/nextseek-api/` ships empty on purpose**: a placeholder keeps its `COPY` working.
- **`ns-sidecar/app/contract.py` and the plugin's `cc-runtime/build_context/plugins/nextseek/bin/_ws_contract.py` are one contract in two copies.** Both name a parity test, `test_ws_contract_parity.py`, that does not exist. They are byte-identical today and nothing would say if they drifted.
- **Each `PORT-EVIDENCE.json` records a named developer's home path, pinned by equality in three port tests.** You cannot scrub it without reddening them, and never copy it into a doc.
- **`bedrock-proxy/proxy-secret.env` is ignored only by the `**/proxy-secret.env` rule.** On each box it is moved by hand; `stat` and `git check-ignore -v` it after the move.

## Test command

See `NessieAI/tests/README.md` ("cc-runtime" rows).

## See also

- `NessieAI/docker/README.md`: what each context ships.
- `NessieAI/docker/cc-runtime/container/CLAUDE.md`: what the agent is told.
- `NessieAI/cc/CLAUDE.md`: the host side of the sandbox.
- `docker/CLAUDE.md`: nginx, entrypoint, ports and env rules for the rest of the stack.
