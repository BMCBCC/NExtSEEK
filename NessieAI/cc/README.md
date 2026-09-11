# `nextseek_api/cc_assistant/`

## What this is

The Container-CC subsystem: the per-turn **route decision** for the chat assistant, and
the **sandbox** that runs a headless Claude Code agent as an ephemeral sibling container
when that decision is `container_cc`.

It is a real Django app — installed as
`nextseek_api.cc_assistant.apps.CcAssistantConfig` at `dmac/settings.py:179` — but an
unusual one. It declares **no models and no migrations of its own**; the ORM row it
writes is created at `NessieAI/router/turn_ledger.py:28`, from a model class
defined in `nextseek_api/assistant/models_db.py`. Its `AppConfig.ready()` hook exists
solely to arm the LLM cost ledger (`nextseek_api/cc_assistant/apps.py:9-11`). It
registers **no URLs**: the single HTTP surface is a ViewSet registered from outside the
boundary at `nextseek_api/urls.py:40`.

So the package is a library of engine parts, not a request handler. Two thirds of it is
test code — 202 Python files, 143 of them under `tests/`.

Three route constants define the whole decision space —
`NessieAI/router/router.py:30-32` — `nextseek_query`, `container_cc`,
`unrelated`.

## Surface

**Routing.** `decide()` at `NessieAI/router/router.py:308` is the one public
entry point. Beneath it sit three route-choosing strategies, tried in order. A
comparative-posterior selector goes first when its Django feature flag is on
(`NessieAI/router/posterior_selector.py:38`); a returned selection
short-circuits the rest at `NessieAI/router/router.py:285-286`, so the BAML
router is never consulted. Otherwise a BAML router picks a destination — fed by a
classifier that assigns a task family rather than a route — and a keyword regex
(`NessieAI/router/router.py:107`) is the last resort when BAML is unreachable.
No `dmac_assistant` import sits at module scope in this package's non-test code — an
absence no single line can show, established by searching the tree; some test modules do
import it at module scope. Every non-test site is inside a function body, including the
loader at `NessieAI/router/router.py:135-139`. Two
telemetry-only overlays observe the outcome without changing it:
`NessieAI/router/risk_overlay.py:1` and
`NessieAI/router/route_monitoring.py:1`. The classifier's label space is owned
by the `nessie_tests` corpus, not by this package
(`NessieAI/router/family_labels.py:21`).

**The sandbox.** `run_cc_turn()` at `NessieAI/cc/cc_engine.py:1005`
is the turn driver, inside the largest file here
(`NessieAI/cc/cc_engine.py:1908` is its last line). Its pieces:

| Concern | Where |
|---|---|
| Complete agent env, single source of truth | `NessieAI/cc/cc_engine.py:282` |
| Mount payloads, one named volume, per-mount subpath | `NessieAI/cc/cc_engine.py:932` |
| Fail-closed check that each subpath dir exists | `NessieAI/cc/cc_engine.py:988` |
| Wall-clock clamp for a single turn | `NessieAI/cc/cc_engine.py:103` |
| Secret-scrub watermark for a stored transcript | `NessieAI/cc/cc_engine.py:527` |
| Agent image default | `NessieAI/cc/cc_engine.py:49` |
| Dedicated network default | `NessieAI/cc/cc_engine.py:59` |

Around it: `NessieAI/cc/attach.py:1-9` demultiplexes Docker's stdcopy
framing (copied verbatim from upstream with attribution, because the upstream module
drags in FastAPI); `NessieAI/cc/translate.py:1-7` maps Claude Code
`stream-json` onto the six progress events the existing React frontend already renders;
`NessieAI/cc/cc_artifacts.py:3` decides what becomes a downloadable
bundle; `NessieAI/cc/cc_transcript_store.py:3-4` zstd-compresses the
session `.jsonl` into a DB row.

**Path layout.** `NessieAI/cc/cc_config.py:23` names the external volume
and its mount point, read from env at `NessieAI/cc/cc_config.py:36`;
`NessieAI/cc/cc_config.py:54` holds the cross-session-memory knobs.
`NessieAI/cc/cc_provision.py:99-107` is the single source of truth for
every directory a turn touches, and `NessieAI/cc/cc_provision.py:156`
resolves the caller's SEEK project with the caller's own credentials, failing closed
rather than guessing.

**Background work.** Two Celery tasks: an idle-session summarizer at
`nextseek_api/cc_assistant/cc_sweep.py:91` and a file-upload task at
`nextseek_api/cc_assistant/cc_upload_tasks.py:29`. A third sweep,
`NessieAI/cc/cc_staging.py:253`, moves sidecar-staged artifacts into the
requesting user's own tree.

**Operation registry.** `op_registry/` is the authoritative inventory of the plugin
commands the agent may call. `NessieAI/cc/op_registry/export.py:14`
renders it to the committed `ops.json`; `NessieAI/tests/cc/bin_inventory.py:38`
discovers the executable shims from disk rather than a hardcoded list, rooted at
`NessieAI/tests/cc/bin_inventory.py:19` — 20 `nextseek-*` shims as of
2026-09-02.

**Evidence and gates.** `NessieAI/cc/step7_llm_cost_ledger.py:3` records
real token spend, and `NessieAI/tests/cc/step7_per_op_evidence.py:7-9` keeps the
per-op proof logic pure so it is testable without spending. The paid orchestration is
`NessieAI/tests/cc/scripts/full_ui_e2e.py:2`; the zero-spend re-verifier that
trusts no artifact's own PASS is
`NessieAI/tests/cc/scripts/verify_prod_readiness_manifest.py:2-5`.

Three directories here are **load-bearing inputs the package reads**, not scratch it
writes. `acceptance_evidence/` supplies the gate exercise catalog and the instance
binding (`NessieAI/tests/cc/step7_gate_catalog.py:19` and
`NessieAI/tests/cc/step7_gate_catalog.py:20`). `tests/acceptance_evidence/` is
the home for generated run bundles, and its validator refuses any bundle whose files are
only Markdown
(`NessieAI/tests/cc/acceptance_evidence/step7/README.md:13-16`).
`evidence/` holds a live probe script
(`NessieAI/history/cc/evidence/run_1c_claude_md_live_probe.py:2`).

## Running and testing

Three lanes, not interchangeable.

1. **Hermetic host lane.** No database, no Docker, no spend. I ran this one on
   2026-09-02 and confirmed the result: 908 passed, 22 failed, 5 skipped, 62
   collection errors, in 5.6 seconds. Both the failures and the errors are
   environmental — modules needing `docker`, `chat_nextseek`, or a configured
   Django, under a dependency set that supplies none of them.
2. **In-container clean lane** — the canonical behavioural suite, needing the
   live container's secrets, DB grant and network. (not run)
3. **Paid real-stack acceptance**, gated behind an env flag at
   `NessieAI/tests/cc/test_cc_realstack.py:55`, which spends real
   money on Opus turns through the auth proxy. (not run)

The `host_only` marker declared at `pyproject.toml:148` splits source-tree hygiene tests
out of the in-container run; several test modules here carry it.

## Depends on / depended on by

Depends on, outside this directory:

- `dmac_assistant/`, vendored: its BAML router, loaded at
  `NessieAI/router/router.py:135-139` among other function bodies, and
  `run_tracker.diff_files` at `NessieAI/cc/cc_engine.py:1852`, which is
  not part of the router.
- `nextseek_api/assistant/models_db.py`, imported at `NessieAI/router/turn_ledger.py:4`,
  for the ORM model written at `NessieAI/router/turn_ledger.py:28`.
- `nextseek_api/eval/` for the routing generation store, imported at
  `NessieAI/router/posterior_selector.py:9`, used at
  `NessieAI/router/posterior_selector.py:47`.
- `nessie_tests/corpus.json` for the classifier label space, resolved at
  `NessieAI/router/family_labels.py:21`.
- `seek.seekdb`, used host-side only to resolve a project, imported lazily inside the
  factory at `NessieAI/cc/cc_provision.py:150-151`.
- `docker/cc-runtime/build_context/plugins/nextseek/bin/`, the shim directory the
  registry scans — `NessieAI/tests/cc/bin_inventory.py:22`. Deleting it silently
  empties the op inventory.
- `nextseek_api/assistant/read_safe_endpoints.json`, read eagerly at
  `NessieAI/cc/op_registry/ops.py:19-23`.

Depended on by. Non-test consumers grouped by kind; the many test modules that import
this package are omitted.

- Production. `nextseek_api/services/cc_assistant.py:446` is the ViewSet, and
  `nextseek_api/services/cc_assistant.py:351` picks the route for a query, applying
  overrides in the precedence set out at
  `nextseek_api/services/cc_assistant.py:354`.
  `nextseek_api/management/commands/cc_sweep_staging.py:30` is a management command
  calling `cc_staging.sweep_user_staging` at
  `nextseek_api/management/commands/cc_sweep_staging.py:59`, described at
  `nextseek_api/management/commands/cc_sweep_staging.py:1-12` as the trusted-code
  recovery and capability-gate path for staged strays.
  `nextseek_api/batch_upload/celery_app.py:55-56` imports both task modules to register
  them and schedules the summary sweep every 300 seconds at
  `nextseek_api/batch_upload/celery_app.py:42-43`.
- Mutual. `nextseek_api/eval/` both feeds this package and reads from it —
  `nextseek_api/eval/human_grade_fit.py:24`, `nextseek_api/eval/task6_replay.py:175`,
  `nextseek_api/eval/generation_validation.py:125`.
- Code generation and gates:
  - `build_tools/gen_op_surfaces/route_capabilities.py:1` — the router's
    `route_capabilities.json`; registry imports at
    `build_tools/gen_op_surfaces/route_capabilities.py:8-26`.
  - `build_tools/gen_op_surfaces/skills.py:1` — the SKILL.md capability matrices;
    `build_tools/gen_op_surfaces/skills.py:11-13`.
  - `build_tools/gen_op_surfaces/commands.py:1` — the command-doc surfaces;
    `build_tools/gen_op_surfaces/commands.py:7-9`.
  - `build_tools/gen_op_surfaces/claude_md.py:1` — the container `CLAUDE.md` plugin,
    skill and operation inventories; `build_tools/gen_op_surfaces/claude_md.py:16-21`.
  - `build_tools/gen_op_surfaces/docker_blocks.py:1` — emits and validates the
    Dockerfile plugin `COPY`/`PATH` and Compose named-context blocks;
    `build_tools/gen_op_surfaces/docker_blocks.py:12-17`.
  - `build_tools/plan005_validate_plugins/validate.py:10-17` validates the plugin tree
    against the registry; `build_tools/plan005_gate.py:26-27` pins two test modules here
    as named CI lanes by path string, not by import.
- Verification scripts, importing or reading this package directly:
  `scripts/plan018_v4_9_functional_e2e.py:31`, `scripts/plan018_v4_5_verifier.py:50`,
  `scripts/plan018_v4_9_task8_deploy.py:1643` and
  `scripts/plan018_v4_9_task8_deploy.py:1855`.
- Test harness. `nessie_tests/sources.py:254` is not an import that file performs: it is
  probe source inside the `_CONTAINER_PY` string literal opened at
  `nessie_tests/sources.py:245`, executed inside the container.

See `NessieAI/cc/CLAUDE.md` for the invariants and traps.
