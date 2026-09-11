# Working in `nextseek_api/cc_assistant/`

## Invariants

These hold today and are enforced by tests. Breaking one is a security or
correctness regression, not a refactor.

- **One function builds the agent's environment.** `NessieAI/cc/cc_engine.py:282-297`
  is the sole constructor, and both the turn driver and the containment canary
  call it, so an inline dict elsewhere cannot smuggle a credential in. The agent
  carries zero AWS credentials and none of the shared backend passwords; it
  reaches the model only through the auth proxy and reaches data only through
  the authenticated REST API as the logged-in user.
- **Network segmentation is the containment control**, not filesystem
  permissions. The sibling joins the network named at
  `NessieAI/cc/cc_engine.py:59`, declared as `dmac-cc-net` in the top-level
  `networks:` block of `docker-compose.yml` and marked `internal: true` there, so it
  has no gateway at all. `db`, `neo4j`, `seek`
  and `solr` declare no `networks:` key and so stay on the default network
  only. Adding the agent
  to the default network would hand it L3 reach to services whose password is a
  committed default.
- **Every mount is a subpath of one named volume.** `NessieAI/cc/cc_engine.py:932`
  builds them and takes each subpath value verbatim from the provisioner —
  never by string-stripping a prefix. Interpolating an unvalidated segment into
  a subpath is a cross-user read.
- **Directory names are validated before interpolation.** Project, user,
  session and run identifiers each pass the same segment check —
  `NessieAI/cc/cc_provision.py:116-121`.
- **The `shared` tree is project-scoped and deliberately carries no user
  segment** — `NessieAI/cc/cc_provision.py:130`. That asymmetry is
  the design, not a bug.
- **Scratch mounted into an agent is per-turn, never the user-scoped root.**
  The mount takes the run-scoped subpath at
  `NessieAI/cc/cc_engine.py:972`, which exists only when a run id
  was supplied — `NessieAI/cc/cc_provision.py:141`. Two turns must
  not be able to see or overwrite each other's files.
- **Spawn fails closed when a backing directory is missing**
  (`NessieAI/cc/cc_engine.py:988`), because the Docker Engine
  refuses a subpath mount whose directory does not already exist. <!-- UNVERIFIED: the Engine behaviour is asserted by the guard's own docstring, not confirmed against Docker here -->
- **Server-side clamping beats any client value.** The Debug panel's turn-length
  control is bounded at `NessieAI/cc/cc_engine.py:103`; the UI can
  never raise the ceiling the deployment set.
- **A transcript is summarized only if it is watermarked as scrubbed.** The
  Celery beat holds no user credential and so cannot scrub, so it gates on
  `NessieAI/cc/cc_engine.py:527` and skips anything unverified.
  A session that keeps warning every beat is the intended operator signal. <!-- UNVERIFIED: operator intent, stated in the module docstring at nextseek_api/cc_assistant/cc_sweep.py:12, not observable in code -->
- **Only the staging sweep writes into a user's own subtree.** The sidecar's
  volume mount is pinned to the reserved staging subpath at
  `docker-compose.yml:183`, so it cannot reach `{project}/{user}/` at all, and
  the sweep derives its destination only from the validated request identity
  (`NessieAI/cc/cc_staging.py:274-276`, enforced at
  `NessieAI/cc/cc_staging.py:279`) — never from a staged file's
  name.
- **BAML imports stay lazy and guarded.** `NessieAI/router/router.py:135`
  defers the loading, and the handler at
  `NessieAI/router/router.py:228-230` turns a failure into a fallback
  instead of an exception. A vendoring or dependency hiccup must degrade routing,
  never stop Django from booting.
- **`op_registry/__init__.py` must stay stdlib-only.** Attribute access is
  routed through the lazy `__getattr__` at
  `NessieAI/cc/op_registry/__init__.py:61` precisely so importing
  the package does not drag in pydantic.
- **`ops.py` is the registration source of truth**; `ops.json` is generated
  output written by `NessieAI/cc/op_registry/export.py:14`. Never
  hand-edit the JSON.

## Landmines

- **`.vetting/` is not documentation.** 65 files of superseded automated
  review-iteration logs; the one cited here records a single hardening pass over
  a plan document —
  `NessieAI/history/cc/archive/.vetting/plan-3-phase2-fix-log-iter22.md:1-4`. Do
  not read them for current behaviour and do not cite them.
- **The 10 `SPEC-*.md` / `PLAN-*.md` files here are superseded** and are
  scheduled to move to an archive. The one cited announces itself as live state:
  `NessieAI/history/cc/archive/PLAN-3-ui-based-io.md:3` claims "TRUE STATE" as of a
  date months past. That framing is why they mislead.
- **`archive/LIVE_EVIDENCE.md` and `DEPLOY.md` are stale and under separate triage.**
  `NessieAI/history/cc/archive/LIVE_EVIDENCE.md:8-10` documents a test-runner
  limitation on one box at one moment, which readers keep mistaking for a
  standing constraint.
- **`acceptance_evidence/` is read at import time, not at test time.**
  `NessieAI/tests/cc/step7_gate_catalog.py:18` binds the catalog
  directory, and `NessieAI/tests/cc/step7_gate_catalog.py:25` scans the
  plugin bin directory — both at module scope. Moving or emptying either
  directory turns a passing suite into import errors.
- **`evidence/` is likewise load-bearing.** A test loads a probe script out of
  it by relative path at `NessieAI/tests/cc/test_cc_scripts_attribution.py:430`.
- **`op_registry/ops.py` reads a JSON file from a sibling app at import**
  (`NessieAI/cc/op_registry/ops.py:19`). If
  `nextseek_api/assistant/read_safe_endpoints.json` moves, the whole registry
  stops importing.
- **The hermetic lane printed at `DEPLOYMENT.md:482` cannot collect as written.**
  Its dependency list omits Django while modules here import Django at module
  scope — `NessieAI/router/posterior_selector.py:6` is one — so 62
  modules error before any test runs. Measured 2026-09-02. Add
  Django to the `--with` list, or pass `--continue-on-collection-errors`.
- **There is no `conftest.py` anywhere under `tests/`.** The settings module
  named at `pyproject.toml:147` is the real one, not the test one, so a bare
  root-level `pytest` over this directory behaves unlike any documented lane.
- **`cc_engine.py` runs to `NessieAI/cc/cc_engine.py:1908` and
  holds several distinct concerns.** Read the section you need; it is not a
  narrative.
- **`router.py` opens with a `try/except ImportError` dual import**
  (`NessieAI/router/router.py:14-17`) so the module also loads outside
  the package. Adding a plain relative import to the top of that file breaks
  the standalone path silently.
- **Adding an operation is a skill, not an edit.** A hand-rolled parallel
  catalog passes its own tests and then fails the generated-surface check at
  `.claude/skills/add-cc-op/SKILL.md:78`.
- **`NessieAI/tests/cc/test_cc_realstack.py:55` spends real
  money** when its env flag is set. Do not set it casually.

## Test command

The canonical behavioural suite, run inside the live container so it has the
database grant and the secrets:

```
docker exec -w /app nextseek uv run --no-sync python -m pytest \
  NessieAI/tests/cc/ --create-db -k 'not realstack' \
  --ignore=NessieAI/tests/cc/test_step7_compose_deploy.py \
  --ignore=NessieAI/tests/cc/test_cc_realstack.py
```

(not run) — it needs a running stack. Never widen it to the whole
`nextseek_api/` tree in-container; that path carries hundreds of known
environmental harness errors that are not regressions.

## See also

- See `NessieAI/cc/README.md` for what each module does, the
  dependency map in both directions, and the three test lanes.
- See `DEPLOYMENT.md:480-486` for the full lane table and the deployment
  runbook.
- See `NessieAI/cc/DEPLOY.md:15` for subsystem-specific deploy
  notes — pending review, treat as unverified.
- See `docker/cc-runtime/Dockerfile:51` for how the agent image and its plugin
  bin directory are assembled, and the build-time guard at
  `docker/cc-runtime/Dockerfile:60` that refuses to ship an empty catalog.
- See the repo-root `CLAUDE.md` for the router overrides, the sticky-CC rule,
  and where the ViewSet lives.
