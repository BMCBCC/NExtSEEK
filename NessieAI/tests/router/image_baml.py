"""The BAML tree the cc-agent image build reads, resolved the way the build sees it.

The image holds no BAML copy of its own: its Dockerfile COPYs the Compose named
context `dmac_assistant_baml` to /app/baml_src/ and runs `baml-cli generate` there.
This resolves that context from the generated block in `docker-compose.yml`,
through the generator's own parser and validator, so a test can name the file the
image generates from and compare it with the file Django runs.
"""
from __future__ import annotations

from pathlib import Path

from NessieAI import paths
from NessieAI.build_tools.gen_op_surfaces.constants import COMPOSE_REL, NAMED_BAML_CONTEXT
from NessieAI.build_tools.gen_op_surfaces.docker_blocks import (
    parse_additional_contexts_block,
    validate_compose_named_context,
)


def image_baml_dir(repo_root: Path = paths.REPO_ROOT) -> Path:
    """Return the directory the image's BAML COPY reads; raise if it is not safe."""
    compose_text = (repo_root / COMPOSE_REL).read_text(encoding="utf-8")
    return validate_compose_named_context(
        repo_root=repo_root,
        contexts=parse_additional_contexts_block(compose_text),
        name=NAMED_BAML_CONTEXT,
    )


def image_baml_source(name: str) -> Path:
    """Return the file the image build generates from for BAML file ``name``."""
    return image_baml_dir() / name
