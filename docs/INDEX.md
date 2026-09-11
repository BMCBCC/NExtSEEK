# docs/

Cross-cutting documentation only: things that belong to no single folder.
A folder's own docs live beside its code (`README.md`, plus `CLAUDE.md` when it has rules).
A doc that tracked code cites must itself be tracked, or the citation points at a folder README.

## Current

| File | Kind | Read when | Tracking issue |
|---|---|---|---|
| [`ISSUE-CONVENTIONS.md`](ISSUE-CONVENTIONS.md) | convention | filing any GitHub issue; `scripts/validate_issue.py` enforces it | |
| [`endpoint-authorization-register.md`](endpoint-authorization-register.md) | register | changing who may call an endpoint. Incomplete for routes added after 2026-08-11; `ci/routes.py` is the full route list. Its `is_staff` question was ruled by #74 and #75 (admin means `is_superuser`); its per-endpoint buckets are still open under #64 | #64 |
| [`neo4j-programmatic-access.md`](neo4j-programmatic-access.md) | runbook | querying Neo4j over HTTP, Browser or bolt, or rotating its password | |
| [`sample-download-workflow.md`](sample-download-workflow.md) | explanation | changing any "Download samples" control or the workbook | |
| [`UI.md`](UI.md) | snapshot | finding a page's route, view and template. Dated 2026-09-03; check it against the tree | |
| [`superpowers/specs/2026-09-01-nextseek-ci-comprehensive-coverage-design.md`](superpowers/specs/2026-09-01-nextseek-ci-comprehensive-coverage-design.md) | live spec | extending CI coverage past tier T0 | #104 |

`docs/superpowers/` is gitignored by default; only files named by a negation in `.gitignore` are tracked.

## Elsewhere

- Nessie docs are listed in [`NessieAI/README.md`](../NessieAI/README.md).
- Superseded docs: [`archive/INDEX.md`](archive/INDEX.md) for everything outside Nessie,
  [`NessieAI/history/INDEX.md`](../NessieAI/history/INDEX.md) for Nessie.
