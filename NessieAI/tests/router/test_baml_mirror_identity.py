"""The cc-runtime BAML mirror is byte-identical to the canonical tree, all 8 files.

`NessieAI/dmac_assistant/baml_src/` is canonical. `NessieAI/docker/cc-runtime/baml_src/`
is a hand-kept copy: the agent image build copies it and runs `baml-cli generate` over
it (`NessieAI/docker/cc-runtime/Dockerfile`), so a drifted copy ships a different
prompt or schema in the image than the one Django runs. Until the Phase C dedupe
leaves one tree, every file must match byte for byte and neither tree may hold a
file the other lacks.

The older pairwise checks in `test_router_family.py`, `test_baml_router_schema.py`
and `test_router_v46_mutations.py` cover only `router.baml` and `classifier.baml`.
"""
from __future__ import annotations

import pytest

from NessieAI import paths

CANONICAL = paths.DMAC_ASSISTANT_DIR / "baml_src"
MIRROR = paths.CC_RUNTIME_DIR / "baml_src"

# Adding or removing a BAML file means editing this tuple, so the change is made
# on purpose and in both trees.
BAML_FILES = (
    "classifier.baml",
    "clients.baml",
    "functional_evaluator.baml",
    "generators.baml",
    "judge_router.baml",
    "judge_ui.baml",
    "router.baml",
    "summarize.baml",
)


def _baml_names(root):
    # rglob over a missing directory yields nothing, so without this assert the
    # listing check would compare two empty lists once a root moved.
    assert root.is_dir(), f"BAML tree not found at {root}"
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*.baml"))


def test_canonical_tree_holds_exactly_the_eight_baml_files():
    assert _baml_names(CANONICAL) == sorted(BAML_FILES)


def test_mirror_tree_holds_exactly_the_eight_baml_files():
    assert _baml_names(MIRROR) == sorted(BAML_FILES)


@pytest.mark.parametrize("name", BAML_FILES)
def test_mirror_copy_is_byte_identical_to_canonical(name):
    canonical = (CANONICAL / name).read_bytes()
    mirror = (MIRROR / name).read_bytes()
    if canonical == mirror:
        return
    offset = next(
        (i for i, (a, b) in enumerate(zip(canonical, mirror)) if a != b),
        min(len(canonical), len(mirror)),
    )
    line = canonical[:offset].count(b"\n") + 1
    pytest.fail(
        f"{name}: the cc-runtime mirror differs from the canonical copy at byte "
        f"{offset} (line {line}); sizes {len(canonical)} vs {len(mirror)}. Edit the "
        f"canonical file and copy it over the mirror."
    )
