# `NessieAI/build_tools/`

## What this is

Three independent command-line tool groups that produce or check
**committed-but-generated** files elsewhere in the repo. It is not a library: only
tests import it from outside this directory
(`NessieAI/tests/router/test_route_capabilities.py:17`,
`NessieAI/tests/cc/test_future_op_dropin.py`,
`NessieAI/tests/cc/test_plugin_container_claude_md.py`), so no production code path
runs any of this. The tools are run by hand, by a documented skill, or by the pytest
suite. The import name is `NessieAI.build_tools`; there is no build system of its own
(no `pyproject.toml`, `uv.lock` or `Makefile` here), so every entry point runs on the
root project's environment.

Two groups are live generators. `gen_op_surfaces` renders the generated targets of the
Container-CC operation registry (`NessieAI/build_tools/gen_op_surfaces/emit.py:217-235`),
and `ingest_nextseek_docs` refreshes the NExtSEEK user-docs snapshot baked into the agent
image from GitBook (`NessieAI/build_tools/ingest_nextseek_docs/constants.py:11-14`). The
third, `plan005_validate_plugins`, validates the installed plugin trees.

The Plan 005 evidence protocol that used to sit beside them (the five `plan005_*`
modules, their sign-offs, schemas and tests) is closed and frozen in
`NessieAI/history/plan005/` (`NessieAI/history/INDEX.md`). Nothing live imports it.

`ingest_nextseek_docs` came from the dmac-assistant repository. The cc-runtime port
record pins source commit `a429f137`
(`NessieAI/docker/cc-runtime/PORT-EVIDENCE.json:2-4`) and names the
module `build_tools.ingest_nextseek_docs` as the upstream entry point it invoked
from that clone (`NessieAI/docker/cc-runtime/PORT-EVIDENCE.json:20-22`); the same commit pins
the image port (`NessieAI/docker/cc-runtime/Dockerfile:4-7`). The copy here carries
NExtSEEK-specific default output paths
(`NessieAI/build_tools/ingest_nextseek_docs/constants.py:18-21`) and two helpers for GitBook's
2026-07 export format, one for a leading llms.txt banner
(`NessieAI/build_tools/ingest_nextseek_docs/fetch.py:94-95`) and one for a repeated trailing
agent-instructions block (`NessieAI/build_tools/ingest_nextseek_docs/fetch.py:114-115`).

`gen_op_surfaces` is the **generator** end of a contract the operation registry
documents from the consumer end. See `NessieAI/cc/README.md` for the registry.

## Surface

The surface here is **command-line entry points plus the file sets each reads and
writes**, not a public Python API. What follows is grouped by entry point, with the
inputs and the outputs named.

### `python -m NessieAI.build_tools.gen_op_surfaces`

`--check` and `--write` are mutually exclusive and one is required; `--root` defaults
to the repo root and `--tmpdir` steers check-mode
rendering (`NessieAI/build_tools/gen_op_surfaces/__main__.py:15-42`). `--check` renders every
target into a temporary directory and byte-compares the committed file
(`NessieAI/build_tools/gen_op_surfaces/emit.py:261-295`); `--write` writes only the targets
whose bytes differ (`NessieAI/build_tools/gen_op_surfaces/emit.py:298-314`). Exit codes are 0
for no change, 1 for error, 2 for changes written
(`NessieAI/build_tools/gen_op_surfaces/constants.py:11-13`).

The target registry (`NessieAI/build_tools/gen_op_surfaces/emit.py:217-235`) holds two
whole-file targets and a set of marked blocks:

| Generated target | Kind | Emitter |
|---|---|---|
| `NessieAI/dmac_assistant/build_context/route_capabilities.json` | whole file | `NessieAI/build_tools/gen_op_surfaces/route_capabilities.py:327-328` |
| `NessieAI/docker/cc-runtime/build_context/plugins/nextseek/context/capabilities.md` | whole file | `NessieAI/build_tools/gen_op_surfaces/emit.py:81-88` |
| `NessieAI/docker/cc-runtime/Dockerfile` plugin `COPY`, plugin `PATH`, capabilities `COPY` | 3 blocks | `NessieAI/build_tools/gen_op_surfaces/docker_blocks.py:48-73` |
| `docker-compose.yml` additional build contexts (`chat_nextseek`, `dmac_assistant_baml`) | 1 block | `NessieAI/build_tools/gen_op_surfaces/docker_blocks.py:76-80` |
| `NessieAI/docker/cc-runtime/container/CLAUDE.md` plugin, skill and operation inventories | 3 blocks | `NessieAI/build_tools/gen_op_surfaces/claude_md.py:146-190` |
| each plugin `commands/*.md` carrying the command-ops markers | 1 block each | `NessieAI/build_tools/gen_op_surfaces/commands.py:39-69` |
| each installed `SKILL.md` | 1 block each | `NessieAI/build_tools/gen_op_surfaces/skills.py:107-146` |

Marked-block targets are discovered from disk rather than hardcoded: command docs by
scanning each plugin's `commands/*.md` for the marker pair
(`NessieAI/build_tools/gen_op_surfaces/commands.py:72-93`), skills from the install oracle's
own discovery (`NessieAI/build_tools/gen_op_surfaces/skills.py:149-169`), and the Dockerfile,
Compose and container-`CLAUDE.md` blocks only when both markers are already present
in the file (`NessieAI/build_tools/gen_op_surfaces/emit.py:127-214`).

Two path constants define the capabilities contract: the canonical document under
`NessieAI/chat_nextseek/` and the baked copy under the plugin tree
(`NessieAI/build_tools/gen_op_surfaces/constants.py:26-31`). The emitter for the baked copy is
a straight byte read of the canonical, with no parsing or rewriting
(`NessieAI/build_tools/gen_op_surfaces/emit.py:81-88`). The image, however, does not consume
the baked copy: the Dockerfile first copies the whole plugin directory and then
overwrites that one file from a named `chat_nextseek` build context
(`NessieAI/docker/cc-runtime/Dockerfile:50-55`), which the generator both emits
(`NessieAI/build_tools/gen_op_surfaces/docker_blocks.py:67-73`) and validates as the final
writer of that in-image path
(`NessieAI/build_tools/gen_op_surfaces/docker_blocks.py:143-169`).

The second named context, `dmac_assistant_baml`, is the canonical BAML tree
`NessieAI/dmac_assistant/baml_src/` itself (`NAMED_BUILD_CONTEXTS` in
`NessieAI/build_tools/gen_op_surfaces/constants.py`), so the agent image has no BAML copy to
drift. Its Dockerfile `COPY` sits outside the marked blocks, and `validate_baml_context_copy`
in `NessieAI/build_tools/gen_op_surfaces/docker_blocks.py` holds it to being the only writer
of `/app/baml_src/`. `validate_compose_named_contexts` checks every declared context against
its own tree, and `parse_additional_contexts_block` reads the committed block back for the tests.

Because targets are rendered in sorted order by path
(`NessieAI/build_tools/gen_op_surfaces/emit.py:235`), `NessieAI/dmac_assistant/...` sorts ahead of
`NessieAI/docker/...`, so `route_capabilities.json` is rendered first and its own
byte-identity precondition on the capabilities pair
(`NessieAI/build_tools/gen_op_surfaces/route_capabilities.py:230-233`) is what a stale baked
copy trips, before the whole-file comparison at
`NessieAI/build_tools/gen_op_surfaces/emit.py:288-295` is ever reached.

Every marked block is rewritten in place between its markers only, after a check
that exactly one well-ordered, non-nested marker pair exists
(`NessieAI/build_tools/gen_op_surfaces/blocks.py:9-50`). Path resolution rejects absolute
paths, `..` traversal and symlinks pointing outside the root
(`NessieAI/build_tools/gen_op_surfaces/paths.py:12-42`).

### `python -m NessieAI.build_tools.ingest_nextseek_docs`

Fetches the Koch Institute GitBook site index and its Markdown pages
(`NessieAI/build_tools/ingest_nextseek_docs/fetch.py:43-91`), refetching until two attempts
hash identically, up to three tries, and aborting without writes if they never agree
(`NessieAI/build_tools/ingest_nextseek_docs/__main__.py:101-145`). It writes numbered section
files and a `README.md` into `NessieAI/docker/cc-runtime/docs/nextseek/`, replaces the
`NEXTSEEK-DOCS` marked block inside `NessieAI/docker/cc-runtime/container/CLAUDE.md`, and
stores the content hash (`NessieAI/build_tools/ingest_nextseek_docs/__main__.py:64-81`). The
generated README carries a do-not-edit banner naming this tool by its pre-move path
(`NessieAI/docker/cc-runtime/docs/nextseek/README.md:3`); the next run rewrites it.
`--force`, `--doc-url`, `--docs-dir` and `--claude-md-path` are the flags
(`NessieAI/build_tools/ingest_nextseek_docs/__main__.py:189-209`); exit codes match the other
generator, 0 / 1 / 2 (`NessieAI/build_tools/ingest_nextseek_docs/__main__.py:32-34`). The
`CLAUDE.md` rewrite is atomic through a temp file and `os.replace`
(`NessieAI/build_tools/ingest_nextseek_docs/toc.py:83-90`).

### `python -m NessieAI.build_tools.plan005_validate_plugins`

Hashes each installed plugin tree and runs `claude plugin validate --strict` inside a
network-disabled container against a read-only bind mount of the plugin directory
(`NessieAI/build_tools/plan005_validate_plugins/docker_runner.py:16-44`). `--repo-root` is
required, and `--skip-docker` reduces it to the local identity checks
(`NessieAI/build_tools/plan005_validate_plugins/__main__.py:20-51`). The validator image is
pinned to one digest and any substitute is refused
(`NessieAI/build_tools/plan005_validate_plugins/validate.py:75-80`).

## Running and testing

Tests are in `NessieAI/tests/build_tools/` (`unit/`, `integration/` and the directory
root); the command is the Django lane in `NessieAI/tests/README.md`. It runs over a
read-only mount of the checkout, which is also how the project's own no-write oracle
exercises the generators
(`NessieAI/tests/build_tools/unit/test_gen_op_surfaces.py:273`, asserting at
`NessieAI/tests/build_tools/unit/test_gen_op_surfaces.py:311-318`). A host
`uv run pytest` is not an option: `uv sync` fails building `mysqlclient` on a host
without MySQL client headers.

The `integration` name is not a network lane: its source-contract test monkeypatches the
fetcher (`NessieAI/tests/build_tools/integration/test_markdown_source_contract.py:44`), as
does every other test that touches GitBook (`NessieAI/tests/build_tools/unit/test_fetch.py:36`).

The failures this lane shows are recorded in `ci/pytest-baseline.txt` and have two
causes: the stale baked capabilities copy (`NessieAI/build_tools/CLAUDE.md`), and three
tests that shell out to `git show` against a pinned revision
(`NessieAI/tests/build_tools/unit/test_gen_op_surfaces_claude_md.py:70-71`), which a
container mount of a worktree cannot reach.

CI runs this directory in the no-stack lanes step of `.github/workflows/ci-pytest.yml`;
failing tests there are scored by the diff against `ci/pytest-baseline.txt`, not by
requiring green.

## Depends on / depended on by

**Depends on.** Import edges out of this directory, plus the files and binaries the
tools read by path:

- `NessieAI.cc.op_registry` is the data source for every generated op
  surface, imported at module scope by five modules here:
  `NessieAI/build_tools/gen_op_surfaces/commands.py:12-14`,
  `NessieAI/build_tools/gen_op_surfaces/skills.py:13-15`,
  `NessieAI/build_tools/gen_op_surfaces/claude_md.py:18-23`,
  `NessieAI/build_tools/gen_op_surfaces/docker_blocks.py:19-24` and
  `NessieAI/build_tools/gen_op_surfaces/route_capabilities.py:10-28`.
- `NessieAI/build_tools/plan005_validate_plugins/validate.py:11-18` is the sixth importer of
  that registry, taking the install oracle and the plugin-identity loader.
- `NessieAI.tests.nessie_tests` is imported at module scope by the route-capabilities
  generator for its corpus loader, exporter and fingerprint
  (`NessieAI/build_tools/gen_op_surfaces/route_capabilities.py:29-31`): one of the three
  frozen engine-to-harness edges (`NessieAI/CLAUDE.md` "Boundary"). The corpus file itself
  is resolved through `NessieAI/paths.py`
  (`NessieAI/build_tools/gen_op_surfaces/route_capabilities.py:40`).
- `dmac_assistant.router.capabilities` is imported lazily inside a function, so the
  generator round-trips its own output through the real consumer loader before
  returning it (`NessieAI/build_tools/gen_op_surfaces/route_capabilities.py:307-324`).
- `httpx` is imported at module scope by the fetcher
  (`NessieAI/build_tools/ingest_nextseek_docs/fetch.py:10`) but is declared nowhere in the
  repo-root `pyproject.toml`; the only declaration in the tree is the router package's
  (`NessieAI/dmac_assistant/pyproject.toml:21`).
- Django is **not** a dependency, even though every generator reads the registry: no
  line beginning with `import django` or `from django` exists in any file here, and
  importing `NessieAI.build_tools.gen_op_surfaces.route_capabilities` leaves `django`
  out of `sys.modules`.
- `docker`, invoked as a subprocess by the plugin validator
  (`NessieAI/build_tools/plan005_validate_plugins/docker_runner.py:24-44`).
- Load-bearing input directories the tools READ, not scratch they write: the plugins
  root, `NessieAI/docker/cc-runtime/build_context/plugins/`, which every discovery walks.
  `PLUGINS_ROOT_REL` in `NessieAI/build_tools/gen_op_surfaces/constants.py` and
  `DEFAULT_PLUGINS_ROOT_REL` in `NessieAI/build_tools/plan005_validate_plugins/validate.py`
  both derive it from `NessieAI/paths.py`. Move the plugin tree without `paths.py` and the
  generators emit empty blocks.

**Depended on by:**

- Python imports: tests only. `NessieAI/tests/router/test_route_capabilities.py:17` and
  `NessieAI/tests/router/test_route_capabilities.py:22` import the constants
  and the route-capabilities generator directly; two `NessieAI/tests/cc/` modules import
  the generators too.
- Documented workflow: step 7 of `.claude/skills/add-cc-op/SKILL.md` runs
  `gen_op_surfaces --write` then `--check`, and step 8 requires the `--check` run against
  a read-only repo mount.
- Deployment runbook: `DEPLOYMENT.md` §10 says only the marked blocks of the container
  `CLAUDE.md` are generated, and points here.
- CI: the no-stack lanes step of `.github/workflows/ci-pytest.yml` runs this directory's
  tests, and `ci/pytest-baseline.txt` repeats that command in its own header.
- Generated-file provenance: `NessieAI/docker/cc-runtime/docs/nextseek/README.md:3` carries a
  do-not-edit banner naming this tool.

Not dependency edges: the file inventories frozen in `NessieAI/history/` that record
paths under this directory, and the `CITATIONS.txt` files that list modules here as
sources they cited (for example `NessieAI/cc/CITATIONS.txt:71`). Also excluded:
`NessieAI/docker/cc-runtime/pyproject.toml:58-60` mentions `build_tools` only to record
that its coverage scope was removed from a different project's pytest options.

See `NessieAI/build_tools/CLAUDE.md` for the invariants, the live drift and the traps.
