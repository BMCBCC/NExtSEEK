# NessieAI/

All of Nessie, the NExtSEEK chat assistant, except its API surface. The HTTP routes, the ORM
models and the migrations stay in `nextseek_api/`.

This file is a placeholder written with the package skeleton. The docs step of the NessieAI move
replaces it with the full "to change X, edit Y" map.

- `NessieAI/` is a plain Python package, importable from the repo root in every process that
  imports `nextseek_api`. It is not an installed dist and not a Django app.
- Cross-unit paths go through `NessieAI/paths.py`.
- `NessieAI/history/` is frozen: never collected by pytest, never rewritten, kept out of the app
  image.
