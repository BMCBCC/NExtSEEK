# Working in `NessieAI/hibayes/`

HiBayes spans several folders; the map is `NessieAI/hibayes/README.md` "HiBayes lives in
these places". Rules that span units are in `NessieAI/CLAUDE.md`.

## Invariants

Each of these is load-bearing because this package can steer live traffic. Breaking one
is a spend, evidence or routing regression, not a refactor.

- **Observational evidence must never reach the paired fitter.** The type guard at
  `NessieAI/hibayes/fit/fit_boundary.py:28-47` rejects an online row, a mixed batch and
  a forged discriminator alike. Fitting live-traffic rows would let the router's own past
  choices supply the evidence for its future ones, and the resulting posterior would look
  exactly like an experimental one.
- **A publish must carry approved paired provenance, and policy-selected provenance is
  refused outright.** `NessieAI/hibayes/fit/fit_boundary.py:113-126` demands a
  `paired_run_id`, a content hash and registry approval, and
  `NessieAI/hibayes/fit/fit_boundary.py:120-121` rejects any `route_source` other than
  `forced`. Relaxing this publishes a generation whose evidence was chosen by the thing
  it is about to control.
- **Swapping the active generation is a compare-and-swap, not a write.**
  `NessieAI/hibayes/generation_store.py:349-350` refuses a stale expected hash under a
  row lock taken at `NessieAI/hibayes/generation_store.py:309-312`. Dropping the check
  lets two concurrent activators lose one update, and production routing then follows a
  generation nobody chose.
- **Creating or publishing a generation directly is disabled on purpose.** Both entry
  points are stubs that raise (`NessieAI/hibayes/generation_store.py:226-235` and
  `NessieAI/hibayes/generation_store.py:238-242`) and name the authenticated publisher
  as the only route in. Making either one work again reopens a path that writes a
  posterior with no evidence identity behind it.
- **An actor whose name begins with `live:` may not publish or activate.**
  `NessieAI/hibayes/generation_store.py:216-218` and
  `NessieAI/hibayes/generation_store.py:221-223` raise on that prefix. Removing the
  guard lets an automated caller flip production routing with no maintainer in the loop.
- **The delivery is re-authenticated from disk after preparation and before any durable
  write.** `NessieAI/hibayes/human_grade_fit.py:941-954` rebuilds the fit from the
  original path and compares hashes, so a prepared object's own hashes are never the
  authority. Trusting the prepared copy turns a swapped file between preparation and
  publish into an accepted forgery.
- **Every provider call goes through the reservation gate.** A call that skips
  `NessieAI/hibayes/provider_gate.py:33-67` spends outside the approved cap and leaves
  the reconciliation unable to balance; the AST sweep at
  `NessieAI/hibayes/seam_inventory.py:167-173` exists to find exactly that, so adding an
  ungated call site makes that sweep report a defect.
- **A default schedule may not enter the paid lane.**
  `NessieAI/hibayes/paid_run_schedule.py:13-17` raises whether or not the caller passes
  the flag. Wiring a Celery beat straight to a judging run would bill the account with no
  approved manifest behind the charge.
- **Pair identity has to survive into fit input.** `NessieAI/hibayes/fit/v14/pair_rows.py:23-24`
  refuses a route-family aggregate by type, because an aggregate has already discarded
  which arm answered which question. Feeding one in silently converts a paired design
  into an unpaired comparison.
- **`NessieAI/hibayes/enums.py:1` is a vendored surface pinned to an upstream commit**
  and says so on its first line. Editing it in place makes the next upstream sync a
  silent conflict rather than a merge.
- **Never change `PROMPT_VERSION`** in `NessieAI/hibayes/judge_human_compare.py`: it is
  written into judged rows. A judge-schema change touches three files together
  (`NessieAI/README.md` "To change X, edit Y").

## Landmines

- **Three non-test modules hardcode another developer's absolute home directory.**
  `NessieAI/hibayes/judge_human_compare.py:29-34` uses it for both CLI defaults,
  `NessieAI/hibayes/v4_3_verifier.py:39-40` for the replay source, and
  `NessieAI/hibayes/artifact_validity_proposal.py:71` resolves a `Downloads` folder
  under whoever is running it. On any other machine these produce a missing-file error
  that reads like a code fault, and the CLI `--help` output still advertises the default
  as if it were valid.
- **Running the artifact proposal overwrites committed data in the source tree.** Its
  output directory is the package directory itself
  (`NessieAI/hibayes/artifact_validity_proposal.py:72`) and it writes both CSVs there
  (`NessieAI/hibayes/artifact_validity_proposal.py:407-411`). The SHA-256 of the
  committed `artifact_validity_set3_final.csv` is the digest pinned at
  `NessieAI/hibayes/human_grade_fit.py:110` (check it with `sha256sum`), so a
  regenerated copy fails authentication on the next fit rather than being noticed as
  a diff.
- **NumPyro, JAX and ArviZ are undeclared dependencies.** Grepping `pyproject.toml`,
  `uv.lock` and the root `Dockerfile` for `numpyro`, `jax` or `arviz` returns nothing,
  and the app image carries none of the three (it does carry `numpy`, `scipy`,
  `polars`, `fastexcel` and `orjson`). The imports are lazy
  (`NessieAI/hibayes/fit/v14/quality_model.py:145-147`), so the package imports fine and
  only the authoritative MCMC path dies, at call time, inside the app container.
- **The vendored HiBayes runners cannot import in any image this repo builds.** Their
  entry points import the `hibayes` library at module scope
  (`NessieAI/hibayes/fit/vendor/hibayes_artifact_validity/run_hibayes.py:44-47`), and a
  case-insensitive grep for `hibayes` across every `Dockerfile`, `*.toml` and `*.lock`
  in the repo finds no install of it. The only hit is a comment at
  `NessieAI/docker/cc-runtime/pyproject.toml:76-82` placing the dependency in an image
  whose name a repo-wide grep finds nowhere but on that same line. Treat those runners
  as reference material until that image is reconstructed.
- **Two modules name themselves proposals and must not be imported as product code.**
  `NessieAI/hibayes/artifact_validity_proposal.py:5-6` names the module path reserved
  for the real implementation and says plainly not to import it, and
  `NessieAI/hibayes/router_models_proposal.py:3-5` calls itself smoke-tested but wired
  into nothing. Wiring either in ships a hardcoded path and an unowned contract into the
  request path.
- **The paid-seam sweep reads the router by path, not by import.**
  `NessieAI/hibayes/seam_inventory.py:23` takes `router.py` from `NessieAI/paths.py`,
  and a missing router or package raises `FileNotFoundError` rather than scanning
  nothing (`NessieAI/hibayes/seam_inventory.py:130-133`). Rename `router.py` and only
  this sweep notices.
- **Collection needs Django configured.** `NessieAI/tests/hibayes/conftest.py` re-exports
  the fixtures of `nextseek_api/conftest.py`, which imports `django.contrib.auth.models`
  at module scope, so a host-side `pytest` over these tests errors during collection
  before any test runs.
- **`--no-migrations` is what makes the two MySQL modules fail, not a code defect.**
  Under SQLite with migrations off they raise `no such table: eval_approved_run_manifest`.
  Nothing in this package creates that table: the model declares it at
  `nextseek_api/assistant/models_db.py:223` and the parent app's migration builds it at
  `nextseek_api/migrations/0014_generation_activation_and_reservation.py:79`. Reaching for
  `--create-db` over the whole tree instead of using their own lane is the slow wrong turn.
- **The router consults this package only behind an off-by-default flag.**
  `dmac/settings.py:15-18` reads it from the environment and treats anything but
  `1/true/yes/on` as off. A store change that looks inert locally becomes a live routing
  change on any box where that variable is set.
- See `DEPLOYMENT.md` §1 for the golden rules governing any box this package is
  activated on.

## Test command

See `NessieAI/tests/README.md` ("Django lane", and its `hibayes` bullet for the tests
that need a delivery directory or a migrated MySQL store).

## See also

- See `NessieAI/hibayes/README.md` for what each module does, where the rest of HiBayes
  lives, the two edge directions, and why the non-passing tests are environmental.
- See `NessieAI/router/CLAUDE.md` for the traps at the other end of the cycle
  this package is half of.
- See `nextseek_api/assistant/CLAUDE.md` for the model module that owns these tables.
- See `nextseek_api/CLAUDE.md` for the app-wide traps that apply here too.
