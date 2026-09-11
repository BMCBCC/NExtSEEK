"""Where each file of the agent image's plugin context comes from.

The cc-agent Dockerfile writes /app/plugins/nextseek/context/ twice: the plugin
COPY lays down the plugin tree's own context/ files, then the generated
capabilities-copy block COPYs each chat_nextseek context file that has a plugin
twin from the Compose named context ``chat_nextseek`` (NessieAI Phase C: one copy
of each). The last writer of an in-image path decides its bytes.

This replays those COPY lines in order, stdlib only, so a drift guard can compare
the file the agent actually reads instead of assuming it is the plugin tree's.
The named context's path is pinned separately
(``test_committed_compose_block_maps_every_context_onto_its_tree`` in
``NessieAI/tests/build_tools/unit/test_gen_op_surfaces_dockerfile.py``).
"""
from __future__ import annotations

import re
from pathlib import Path

from NessieAI import paths

DOCKERFILE = paths.CC_RUNTIME_DIR / "Dockerfile"
PLUGIN_CONTEXT_DIR = paths.CC_PLUGIN_DIR / "context"
CANONICAL_CONTEXT_DIR = paths.CHAT_NEXTSEEK_DIR / "src" / "chat_nextseek" / "context"
IMAGE_CONTEXT_DIR = "/app/plugins/nextseek/context"
NAMED_CONTEXT = "chat_nextseek"

_PLUGIN_COPY = re.compile(
    r"^COPY\s+build_context/plugins/nextseek/\s+/app/plugins/nextseek/\s*$"
)
_NAMED_CONTEXT_COPY = re.compile(
    rf"^COPY\s+--from={NAMED_CONTEXT}\s+src/chat_nextseek/context/(?P<src>[^/\s]+)"
    rf"\s+{re.escape(IMAGE_CONTEXT_DIR)}/(?P<dest>[^/\s]+)\s*$"
)


class ImageContextError(ValueError):
    """Raised when a COPY into the plugin context is not one this helper models."""


def _context_files(directory: Path) -> set[str]:
    return {p.name for p in directory.iterdir() if p.is_file()}


def image_context_sources(dockerfile_text: str | None = None) -> dict[str, Path]:
    """Return {in-image context file name: the checkout file its bytes come from}."""
    text = DOCKERFILE.read_text(encoding="utf-8") if dockerfile_text is None else dockerfile_text
    sources: dict[str, Path] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("COPY"):
            continue
        if _PLUGIN_COPY.match(stripped):
            for name in _context_files(PLUGIN_CONTEXT_DIR):
                sources[name] = PLUGIN_CONTEXT_DIR / name
            continue
        match = _NAMED_CONTEXT_COPY.match(stripped)
        if match:
            if match.group("src") != match.group("dest"):
                raise ImageContextError(f"named-context COPY renames its file: {stripped}")
            sources[match.group("dest")] = CANONICAL_CONTEXT_DIR / match.group("src")
            continue
        if IMAGE_CONTEXT_DIR in stripped or stripped.split()[-1].rstrip("/") in (
            "/app/plugins/nextseek",
            "/app/plugins",
        ):
            raise ImageContextError(f"unmodelled COPY into the plugin context: {stripped}")
    return sources


def image_context_files() -> set[str]:
    """The file names the image's plugin context holds."""
    return set(image_context_sources())


def canonical_context_copies() -> set[str]:
    """The in-image context files whose bytes are the canonical chat_nextseek file."""
    return {
        name
        for name, source in image_context_sources().items()
        if source.parent == CANONICAL_CONTEXT_DIR
    }


def image_context_source(name: str) -> Path:
    """The checkout file the image's /app/plugins/nextseek/context/<name> comes from."""
    return image_context_sources()[name]
