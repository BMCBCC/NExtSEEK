"""Repo paths shared across NessieAI units.

Every path join that crosses from one NessieAI unit into another, or out to
the repo root, goes through these constants, so a later move edits one file.

Import-light on purpose: stdlib only, no side effects, and nothing is checked
at import time. A caller that needs a path to exist asserts it itself, so a
missing file fails loudly at the call site instead of here.
"""
from __future__ import annotations

from pathlib import Path

__all__ = [
    "REPO_ROOT",
    "NESSIE_ROOT",
    "CHAT_NEXTSEEK_DIR",
    "NESSIE_CORPUS",
    "DMAC_BUILD_CONTEXT",
    "CC_RUNTIME_DIR",
    "CC_PLUGIN_BIN",
    "READ_SAFE_ENDPOINTS",
]

# NessieAI/paths.py -> parents[0] is NessieAI/, parents[1] is the repo root
# (the host checkout, the /src gate-lane mount, or /app in the image).
REPO_ROOT = Path(__file__).resolve().parents[1]
NESSIE_ROOT = REPO_ROOT / "NessieAI"

# The NS engine unit (dist and import name chat_nextseek); its context/
# catalogs and agent_model_catalog.json live under it.
CHAT_NEXTSEEK_DIR = NESSIE_ROOT / "chat_nextseek"

# The hand-owned test corpus. The live router also reads it (family labels).
NESSIE_CORPUS = NESSIE_ROOT / "tests" / "nessie_tests" / "corpus.json"

# route_capabilities.json (generated) and router_model_class_map.json
# (hand-kept). Stays inside the dmac_assistant unit, next to src/.
DMAC_BUILD_CONTEXT = NESSIE_ROOT / "dmac_assistant" / "build_context"

# Build context of the cc-agent image (dmac-assistant:poc).
CC_RUNTIME_DIR = NESSIE_ROOT / "docker" / "cc-runtime"
CC_PLUGIN_BIN = CC_RUNTIME_DIR / "build_context" / "plugins" / "nextseek" / "bin"

# The granular-op write gate's allowlist. Must stay beside ns/write_gate.py.
READ_SAFE_ENDPOINTS = NESSIE_ROOT / "ns" / "read_safe_endpoints.json"
