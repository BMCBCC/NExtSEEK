# Admin session-inspection endpoint — design

Status: proposed, not built. Investigation done at `origin/dev b1d61979`.

Goal, in the operator's words: *"programmatically give access to all of the
information given that UUID from the URL so that I can easily debug what is
wrong, across all of the various different modes of the Nessie assistant."*

## 1. What the investigation found

### 1.1 The duplicate POSTs are real, and safe to collapse

`cc_assistant.py:787-796` and `:807-816` are character-identical except the
final `force_cc` argument. Both call `_check_auth`, both validate `QueryRequest`,
both 422 the same way.

The forced variant has **no production consumers**. Repo-wide, `cc/query/async`
appears only in docs, tests, evidence files and `ci/routes.py`.
`docs/nessie-blocked-capabilities.md:233` records that even the nessie harness
cannot reach it: *"http_driver.drive posts only to BASE_PATH + '/query/async/'.
There is no per-variant endpoint selector, so the force_cc path is
unreachable."* It is an operator curl surface.

The frontend crosses the two ViewSets: it POSTs to
`cc-assistant/query/async/` (`chat_frontend/src/lib/services/chatApi.ts:78`)
but polls `assistant/tasks/{id}/progress/` (`:181`). The NS progress route is
therefore **not** a dead duplicate and must not be removed with the NS POST.

### 1.2 `cc/query/async` is not admin-gated, and that is deliberate

`CCAssistantViewSet` is `permission_classes = [IsAuthenticated]`; `_check_auth`
checks authentication only. In `_decide_route` (`cc_assistant.py:376`) the test
is `if force_cc or forced == "cc":` — `force_cc` sits outside the `is_admin`
check that nulls `forced`. Any authenticated user gets the identical
`RouteDecision(route=ROUTE_CC, source="forced")`.

This is pinned as intended in three places:
`test_route_override.py:80` (`test_cc_endpoint_still_forces_cc_for_anyone`,
with `USER = is_staff=False, is_superuser=False`), `FAMILIES.json:6863`
("as a NON-admin user"), and `architecture.md:106`.

Consequence to decide deliberately: the admin gate on `force_route="cc"` has
no security value, since the same outcome is one URL away. It still binds for
`"ns"`, because no `force_ns=True` endpoint exists. **Any collapse of the two
POSTs must keep the `force_cc` field un-gated**; folding it into the existing
admin-gated `force_route` would silently remove a capability every non-admin
has today and break the pinned test.

Pre-existing, unrelated: `test_admin_forces_ns` FAILS on dev
(`assert 'baml' == 'forced'`). Its `ADMIN` fixture is `is_staff=True,
is_superuser=False`, encoding the pre-#74 gate. Stale in the safe direction.

### 1.3 Session state is four stores, not two

| Store | Holds | Why it matters here |
|---|---|---|
| `ChatSession` | `results_history` (bundles), `extra_state` (`chat_log`), `last_debug` | the sizes that explained the 1038 and the 2006 |
| `QueryTask` | `status`, `progress` events, `result`, timings | the only record when the session row is empty |
| `TurnLedger` | `route`, `route_source`, `attempted_route`, `task_family` per turn | **written immediately after `route_decided`, before the engine runs** (`cc_assistant.py:529-536`), so it survives a turn that routed and then failed to persist |
| `CCSessionTranscript` | per-turn CC jsonl, zstd, plus `uncompressed_size` | the CC-side transcript; size is stored, so it is free |

`TurnLedger` is the key find for the c0062000 case (0 bundles, 0 chat_log,
task `status=completed`). A ledger row would still be there and would name the
route the vanished turn took.

### 1.4 Prior art to reuse, and one trap

- `bundle_download.bundle_metadata()` already projects a bundle to provenance
  with an `omitted` block naming each bulk payload and its byte size. `_size()`
  is the serializer. Reuse both verbatim.
- `cc_transcript_store.decompress(blob, max_bytes=...)` already decompresses a
  transcript row under a cap.
- `cc-assistant/transcript/<session>/<turn>/` already serves one transcript,
  but is `filter(user=request.user)` scoped and needs the `turn_id` up front.
  **Nothing lists which transcripts exist**, which is the actual gap.
- TRAP: `assistant/sessions/<id>?include=turns` looks like the natural base to
  copy, but it deliberately **hides failed and unrelated turns** (PD-6,
  `assistant.py:592-596`). Those are exactly the turns worth debugging. Do not
  reuse that filter.

## 2. Proposed design

### 2.1 Route and gate

```
GET /nextseek_api/admin/session-debug/<uuid>/
```

Registered `router.register(r"admin/session-debug", views.SessionDebugViewSet,
basename="admin-session-debug")`, following the existing `admin/project-export`
precedent, and declared in `ci/routes.py` in the same commit.

`permission_classes = [IsAuthenticated, IsSuperUser]` — copying
`project_export.py:267`. `IsSuperUser` (`nextseek_api/permissions.py:6`)
already documents why `IsAdminUser` is worthless here. No ownership check:
reading another user's session is the point.

The UUID resolves as `session_id` first, then `task_id`, and the response says
which via `resolved_as`. A task UUID is what appears in logs and error reports,
so accepting it removes a lookup step.

### 2.2 Default response: complete inventory, no bulk payloads

```jsonc
{
  "resolved_as": "session",            // or "task"
  "session":     { session_id, title, user{id,username}, created_at, updated_at,
                   counts: { bundles, chat_log_entries, tasks, ledger_turns,
                             cc_transcripts, files } },
  "sizes":       { results_history_bytes, extra_state_bytes, last_debug_bytes,
                   largest_bundle_bytes, cc_transcript_uncompressed_total },
  "turns":       [ ... ],   // chat_log x bundles x ledger, NOTHING filtered
  "tasks":       [ ... ],   // task_id, status, created/updated, duration_s,
                            // error, progress event NAMES only
  "ledger":      [ ... ],   // turn_number, route, route_source, attempted_route
  "transcripts": [ ... ],   // cc_session_id, turn_id, uncompressed_size, url
  "files":       [ ... ],   // manifest entry + exists + size_bytes AT READ TIME
  "warnings":    [ ... ]
}
```

Sizes and paths, never payloads. Serialising a 13.5 MB `api_result_full` into a
debug response recreates the bug the endpoint exists to diagnose.

### 2.3 `warnings[]` — the part that makes it a diagnostic

Derived checks encoding the three real incidents, so the operator is told the
smell rather than asked to eyeball numbers:

- `updated_at == created_at` while a task reports `completed`
  → *"turn completed but the session was never persisted"* (the c0062000 tell)
- any of the three JSON columns over the MySQL `sort_buffer_size` /
  `max_allowed_packet` thresholds → the 1038 / 2006 tells
- a manifest entry whose `path` does not exist on disk now
- `status=running` with a stale `updated_at` → orphaned task
- `bundles != chat_log_entries`
- a CC turn with no transcript row (the two documented persists-nothing cases)

### 2.4 `?include=` for the bulk, opt-in

`transcripts` (decompressed via the existing helper, under the existing
`CC_TRANSCRIPT_MAX_BYTES` cap), `bundles`, `progress`, `last_debug`, `all`.
Plus `?turn=<n>` to scope to one turn. Same `include` idiom the existing
`get_session` already uses.

This is how "programmatic access to all of it" and "never return a 13.5 MB
payload by default" are both satisfied: everything is reachable, nothing bulky
is automatic.

### 2.5 Modes covered

nextseek_query, container_cc, pipeline/wizard turns (chat_log entry, no
bundle), evaluator sessions (same models via `DictSessionAdapter`), and — the
important one — sessions whose `results_history` is empty, which fall back to
`tasks` + `ledger`.

## 3. Sequencing

1. This endpoint, read-only, additive. Nothing else changes.
2. Only then, as its own change, collapse the two POSTs — keeping `force_cc`
   un-gated per §1.2.

## 4. Risk

Exposes any user's chat titles, queries, replies and output paths to a
superuser. The gate is the only control, so the first test is a **403 for
`is_staff=True, is_superuser=False`** — the exact shape of every logged-in SEEK
user. Paths encode usernames
(`/app/outputs/260907_163856_charlie-test-3/...`); acceptable for an admin
tool, stated rather than discovered. `BioMicroCenter/NExtSEEK` is public, so
tests use synthetic ids only.
