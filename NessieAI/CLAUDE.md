# Working in NessieAI/

Placeholder written with the package skeleton. The docs step of the NessieAI move replaces it.

- NessieAI declares no models, migrations, AppConfig or app label. Engine code that needs the ORM
  imports `nextseek_api.assistant.models_db` and runs only inside a configured Django process.
- Cross-unit paths go through `NessieAI/paths.py`, never a fresh `parents[N]` join.
- Never create `NessieAI/.env`: chat_nextseek's `load_dotenv()` walks up the tree and would find
  it before the repo-root `.env`.
- No `conftest.py` at `NessieAI/tests/` itself. The per-area conftests under `NessieAI/tests/`
  re-export fixtures by name and never declare `pytest_plugins`.
- `NessieAI/history/` is read-only.
