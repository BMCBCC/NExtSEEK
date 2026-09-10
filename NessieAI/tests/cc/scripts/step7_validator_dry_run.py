#!/usr/bin/env python3
"""Hermetic dry-run for Step 7 validator cost-ledger accept/reject paths (Gate 3C).

Exits 0 when:
  - estimate-only synthetic bundle → validator FAILS
  - real-ledger synthetic bundle → validator PASSES (Task 15 matrix checks)

No Docker, network, or live stack required.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

# Run by path, Python puts only this file's own directory on sys.path, so
# NessieAI is not importable. Put the checkout root (the first parent holding
# NessieAI/__init__.py) first. Under `python -m` or an import __package__ is
# set, the root is already importable, and nothing is inserted.
if not __package__:
    for _parent in Path(__file__).resolve().parents:
        if (_parent / "NessieAI" / "__init__.py").is_file():
            sys.path.insert(0, str(_parent))
            break

from NessieAI import paths  # noqa: E402

REPO_ROOT = paths.REPO_ROOT
TESTS = Path(__file__).resolve().parents[1]


def _run_validator(bundle: Path, repo: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "NessieAI.tests.cc.validate_step7_compose_deploy",
         str(bundle), str(repo)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


def main() -> int:
    from NessieAI.tests.cc.step7_compose_fixtures import (
        TRANSCRIPT_CONTENT,
        _full_bundle,
        _repo_with_transcript,
    )

    with tempfile.TemporaryDirectory(prefix="step7-dry-run-") as td:
        root = Path(td)
        repo, sha = _repo_with_transcript(root, content=TRANSCRIPT_CONTENT)
        tracker = root / "tracker" / "integration-plan.json"

        # --- estimate-only bundle must fail cost checks ---
        est_bundle = root / "estimate"
        _full_bundle(est_bundle, tracker, deploy_commit=sha, meta_overrides={
            "matrix_spend_estimate_usd": 0.99,
            "matrix_spend_estimate_method": "synthetic estimate for dry-run",
        })
        (est_bundle / "cost_ledger.json").unlink(missing_ok=True)
        est_code, est_out = _run_validator(est_bundle, repo)
        if est_code == 0:
            print("FAIL: estimate-only bundle unexpectedly passed validator", file=sys.stderr)
            print(est_out, file=sys.stderr)
            return 1
        if "estimate-only rejected" not in est_out and "cost_ledger.json missing" not in est_out:
            print("FAIL: estimate-only bundle failed for unexpected reason", file=sys.stderr)
            print(est_out, file=sys.stderr)
            return 1
        print("OK: estimate-only bundle rejected (exit", est_code, ")")

        # --- ledger bundle must pass (full clean bundle) ---
        ledger_bundle = root / "ledger"
        _full_bundle(ledger_bundle, tracker, deploy_commit=sha)
        ledger_code, ledger_out = _run_validator(ledger_bundle, repo)
        if ledger_code != 0:
            print("FAIL: ledger bundle unexpectedly failed validator", file=sys.stderr)
            print(ledger_out, file=sys.stderr)
            return 1
        if "cost_ledger ok" not in ledger_out:
            print("WARN: ledger bundle passed but cost_ledger detail not found in output")
        print("OK: ledger bundle accepted (exit 0)")

    print("step7_validator_dry_run: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
