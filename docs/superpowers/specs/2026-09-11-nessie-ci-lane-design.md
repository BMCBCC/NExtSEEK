# Nessie CI lane: design

- Date: 2026-09-11
- Branch: `feat/nessie-ci-lane`, cut from `origin/dev` at `f1ef0f3c`
- Status: approved design, not yet implemented. Brainstormed with the operator on 2026-09-11, after three
  read-only research passes (the CI architecture, the Nessie feature surface, and the reusable test tooling).

## 1. Goal

A green run proves one thing: **this build did not break Nessie.** Every Nessie feature exists and answers,
three NS questions and one CC question complete through the real chat page, and the API's view of the
resulting session matches what the page showed.

Not the goal: answer accuracy. That stays with `nessie_tests/`, which the owner drives by hand. A later
increment may wrap its paid full tier in a startup command.

## 2. Decisions

| # | Decision | Choice | Why |
|---|---|---|---|
| 1 | What a green run proves | "This build did not break Nessie" | Quality belongs to `nessie_tests/` |
| 2 | When it runs | After every rebuild of the **app** on a `local` or `dev` box, and on every `./startup.sh ci`. Component rebuilds skip it. `--no-nessie` opts out. Never on `prod` | The operator wants it on every rebuild; four component rebuilds must not pay four times |
| 3 | The questions | Four, in one chat, in this order: "What can you do?", "What mice are treated with NDMA?", "What studies are in IMPACT?" (NS), then "Make me a graph of NHP species" (CC). All routed, none forced | Covers the system-agent, API and graph paths and the CC engine, and tests the real BAML router. NS first and CC last, so sticky CC cannot capture an NS question |
| 4 | Mechanism | Each question is typed and sent in the page; completion and results are checked through the API | The page proves the UI; the API cross-check proves the sessions endpoints report the truth |
| 5 | Accounts | `CI_WRITE_USER` (the existing superuser) drives the page and the admin checks. `CI_SMOKE_USER` is unchanged | Admin controls, `/debug/` and the evaluator reads need a superuser; a separate account would duplicate this one |
| 6 | Failure policy | Any stage that cannot run fails and names the cause, including a provider outage and a misconfigured box | The operator chose "always fail" |
| 7 | Spend | At most 4 chat POSTs per run; the CC turn keeps its existing per-turn cap; reported spend over $1.00 fails the run; NS spend is recorded as unmeasured | A hard ceiling, without building NS cost measurement first |
| 8 | Cleanup | Delete the chat on a pass. On a failure, keep it and print its id and its `/debug/` URL | No pile-up on green runs; full evidence on red ones |
| 9 | Path check | Question 2 must take the API path and question 3 the graph path; a flip fails the test | Covering both paths is why there are two questions. If the planner proves flaky here (#33), downgrade this one check to a warning in the CI record |
| 10 | Base | `origin/dev` | Merges into the NessieAI refactor through git's rename detection (see section 8) |

## 3. What gets built

### 3.1 `ci/smoke/test_nessie.py`: the one file to extend

When Nessie changes, this file changes. Its parts:

- **`QUESTIONS`**: a list of rows, each with the question text, the expected route (`nextseek_query` or
  `container_cc`), the expected path (`system`, `api`, `graph` or `cc`), whether a bundle is expected, and
  whether a CC artifact is expected. A new question is a new row.
- **Module fixtures**
  - `nessie_admin_api`: a `GuardedSession` as `CI_WRITE_USER`, reusing the existing `write_creds` fixture.
  - `nessie_page`: a Playwright context logged in through `/login/` as `CI_WRITE_USER`, the way the existing
    browser fixtures log in. It carries a network guard that counts POSTs to `cc-assistant/query/async/`,
    aborts a fifth one (and fails), and aborts any POST to any other chat-turn route.
  - `chat_run`: sends the questions in order, in one chat, once per module. For each it records the
    `task_id` (from the page's own POST response), the progress events, the reply text, the `bundle_id`,
    the route decision, `cc_turn_meta`, the reported cost and the duration. Completion is detected by polling
    `nessie/tasks/<task_id>/progress/` until a terminal status, not by watching the websocket. Tests read
    this record; no test sends a turn itself.
- **Markers**: the module carries `nessie`, `flow` and `profiles("local", "dev")`.

**Stage 1: everything exists (no model call)**

- Preconditions, checked first: the write credentials are present; `assistant/me` as the write user says
  `is_admin: true`; the write user belongs to a participating project (`assistant/me` answers 200, not 403).
- The page: `/seek/assistant/` renders the chat input (`chat-input`), the send button (`send-button`), the
  New chat button, the saved-chats sidebar, the upload control, the Debug panel (it opens through "Toggle
  debug panel"), the admin route override (`#route-override`), and the JSON and Metadata buttons
  (`json-download`, `metadata-download`), present and disabled.
- Reachability: every GET route in `ci/routes.py` under `assistant/`, `cc-assistant/`, `nessie/`,
  `evaluator/` and `schema_rag/` answers its declared status, each with the account its `auth` names. That
  includes the superuser-only `nessie/sessions/<id>/debug/`, which no test requests today.
- Features: the sessions list; the test cases; `nessie/uploads/`; `schema_rag/retrieve/` returns a non-empty
  endpoint list (it answers 200 even on failure, so the list is what is asserted); the evaluator runs
  listing; a scratch session is created, renamed and deleted.

**Stages 2 and 3: the four questions**

| Question | Route and source | Page | API |
|---|---|---|---|
| "What can you do?" | `nextseek_query`, `baml` | The reply shows; the Debug panel has the route entry | The reply is non-empty; no bundle (the system-agent path ends with `bundle_id=None`) |
| "What mice are treated with NDMA?" | `nextseek_query`, `baml` | The reply shows; JSON and Metadata become enabled; clicking each downloads a file | The bundle JSON parses and carries the full API result; the Metadata download works; the xlsx artifact downloads; the bundle was built by the API path |
| "What studies are in IMPACT?" | `nextseek_query`, `baml` | As above | As above, and the bundle was built by the graph path |
| "Make me a graph of NHP species" | `container_cc`, `baml` | The reply and at least one artifact link show | `cc_turn_meta.model_id` is not null; no 403 and no `query_error`; the CC artifact download works for one file and for the zip; the transcript comes back as ndjson; the reported cost is recorded |

The path for questions 2 and 3 is read from the bundle the turn registered: the graph branch records its
bundle as a graph query (the graph branch of `chat_nextseek/src/chat_nextseek/orchestrator.py`), and the
REST branch records a different mode. The implementer confirms the exact field and values against that code.

**The session cross-check: are the sessions endpoints telling the truth?**

- `assistant/sessions/<s>/?include=turns` has exactly four turns, with the replies the page showed and the
  same bundle ids.
- `nessie/sessions/<s>/debug/` resolves as a session, counts four turns, has a route ledger reading
  `nextseek_query, nextseek_query, nextseek_query, container_cc` with every source `baml`, carries the CC
  transcript and the files list, and reports no warnings. The same endpoint given a `task_id` resolves as a
  task.
- `nessie/sessions/<s>/artifacts/` and `nessie/sessions/<s>/transcript/<turn>/` answer 200 with the real ids.
- The page: after a reload the chat is in the sidebar, and reopening it shows all four turns with the Debug
  panel entries rebuilt.

**Cleanup**: a module finalizer deletes the chat when every test passed. When anything failed it keeps the
chat and writes its id and `/debug/` URL into the CI record.

### 3.2 The route registry (`ci/routes.py`)

- `Route` gains a field `lane: str = ""`. Only `cc-assistant/query/async/` sets `lane="nessie"`, meaning
  "the nessie lane's browser sends this". It keeps `path=None` and `exclude="EXCLUDE_COST"`, so T0 and
  `GuardedSession` still never send it, and the two tests that pin excluded routes stay as they are.
- A new no-stack test pins that exactly one route carries a lane, and that it is this one.
- `GuardedSession` is not widened. The implementer confirms that it refuses a non-GET only under `prod`, so
  the scratch session's POST, PATCH and DELETE to the registered `assistant/sessions/` URLs are allowed on
  `local` and `dev`. The note on the `assistant/sessions/` entry is corrected: today it says the write lane
  POSTs there, and no write-lane test does; the nessie lane will.

### 3.3 Selection (`ci/smoke/pytest.ini`, `ci/smoke/conftest.py`)

- Register the `nessie` marker.
- Add a pytest option `--no-nessie`: when given, every `nessie` test is skipped with that reason.
- **Not** `-m "not nessie"`: `pytest_collection_modifyitems` returns early whenever any `-m` is given, and
  that early return is what keeps the write lane deselected. A `-m` expression would re-admit the write lane.
- On a `prod` profile the module's `profiles` marker skips all of it.

### 3.4 Startup (`startup/ci/runner.py`, `startup/cli.py`, `startup/steps/validate.py`)

- `build_command(..., nessie: bool = True)` appends `--no-nessie` when `nessie` is false.
- `rebuild` turns the lane on only when the component is `app`, and gains `--nessie/--no-nessie` (default on).
  `ci` gains the same flag.
- Stack health gains a Nessie-prerequisites check that runs only when the lane is on: the Bedrock proxy's
  token file has a non-empty `AWS_BEARER_TOKEN_BEDROCK` (its length is checked, the value is never printed),
  the `cc-agent` image exists, and `bedrock-proxy` and `nextseek-sidecar` are running. With the lane on, a
  failure here fails the run before the suite starts and names the missing piece (decision 6). On
  `origin/dev` the token file is `docker/bedrock-proxy/proxy-secret.env`; use the existing path constant, so
  the merge with the refactor, which moves the file, stays a one-line conflict at most.
- The CI record gains a "Nessie" section: for each question the route, source, path, `task_id`, duration and
  reported cost; the total reported spend; and on a failure the kept session id, its `/debug/` URL and the
  evidence folder.
- Evidence on failure: a Playwright screenshot and trace plus the `/debug/` JSON, written under
  `startup/ci-reports/<label>-nessie/`, which is gitignored. Nothing is uploaded.
- `.github/workflows/ci-smoke.yml` (manual dispatch on fairdata-dev) gains a `nessie` boolean input, default
  true, passed through as `--no-nessie` when false.

### 3.5 Frontend (`chat_frontend/`)

- `data-testid`s: `json-download` and `metadata-download` on the two buttons in
  `src/components/Layout/RightSidebar.tsx`; `debug-panel` on the root of
  `src/components/DebugPanel/DebugPanel.tsx`; `debug-entry` with a `data-kind` (`route`, `cc_turn_meta`,
  `agent`, `error`) on each entry; `session-item` on saved-chat rows if they have no test id.
- `e2e/fixtures/ws-mock.ts` intercepts `cc-assistant/query/async/`, the URL `src/lib/services/chatApi.ts`
  posts to, instead of the old `assistant/query/async/`, so the mock Playwright specs test the real path again.
- Rebuild the embedded bundle (`npm run build:embedded`) and commit `static/js/chat_assistant/` as a
  separate second commit. The Docker build has no npm step, so the committed bundle is what ships.

### 3.6 Docs

- `ci/smoke/README.md` gains a "Nessie lane" section: what it proves, when it runs, what it costs, its
  prerequisites (`CI_WRITE_USER` in a participating project with a SEEK project; a non-empty proxy token),
  how to extend it (a question is a row in `QUESTIONS`; a new endpoint is a registry entry plus a check), and
  how to read a failure.
- `ci/README.md` and `DEPLOYMENT.md` gain the prerequisites and the `--no-nessie` flag.
- `ci/CLAUDE.md` gains the `-m` trap from 3.3.

## 4. Timing and spend

- Timeouts: 5 minutes per NS turn (observed mean 38 s, maximum 623 s), 4 minutes for the CC turn (the engine
  stops CC at 180 s), about 12 minutes for the whole lane. Expect roughly 4 to 5 minutes added to a
  rebuild's CI.
- Spend per run: three NS turns (a few cents, unmeasured), one CC turn (observed mean $0.24, cap $0.50), and
  the router calls. The run fails above $1.00 of reported spend.

## 5. Testing the lane itself

- No-stack unit tests: the `QUESTIONS` table's shape; the POST counter and its abort; the spend ceiling; the
  record's Nessie section; the lane pin in the registry; and `--no-nessie` selection, including that the
  write lane stays deselected.
- `startup/tests`: the `build_command` flag, rebuild's component gating, the `ci` flag, and the prerequisites
  check (an empty token fails with a message, and the token value never appears in output).
- Frontend: the existing vitest suite plus a test-id assertion; the mock Playwright project green after the
  `ws-mock.ts` fix.
- Live: one paid run on `local` by the operator (`./startup.sh ci`, about $0.30). The implementation
  workflow stops before it.

## 6. Refinements made while writing this spec

- The brainstorm said T0 would gain a superuser pass so that `/debug/` gets requested. T0 carries a
  deliberate pin, `test_t0_never_sweeps_a_write_auth_route_under_any_profile`, so that pass lives in the
  nessie lane's stage 1 instead, on `local` and `dev` only. T0 is unchanged.
- The opt-out is a `--no-nessie` option, not a `-m` expression (3.3).
- The write gate's blocked path is left to its unit tests. Checking it over HTTP would need `GuardedSession`
  to permit a POST to an `EXCLUDE_COST` route from the requests client, which this design avoids.

## 7. Out of scope

Paid quality runs; measuring NS cost; a startup command for the `nessie_tests/` full tier; the write gate
over HTTP; any run on `prod`.

## 8. Merging into the NessieAI refactor

`ci/` sits at the same path on both branches. Edits under `chat_frontend/` follow git's rename detection to
`NessieAI/chat_frontend/`. `startup/ci/runner.py`, `startup/cli.py` and `startup/steps/validate.py` may
conflict with the refactor's own startup edits; resolve keeping both. Run `scripts/nessieai_codemod.py`
over new Python files. `test_nessie.py` imports only `ci/` modules, the standard library and Playwright, so
expect no rewrites.
