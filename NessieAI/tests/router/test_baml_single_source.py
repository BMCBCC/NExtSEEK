"""One BAML tree: the cc-agent image generates from the canonical files, all 8.

`NessieAI/dmac_assistant/baml_src/` is the only BAML tree. Django's router client is
generated from it by the app image build, and the cc-agent image (the JudgeUITranscript
client behind `tools/e2e/judge_runner.py`) takes the same files through the Compose
named context `dmac_assistant_baml`, which its Dockerfile COPYs to /app/baml_src/.
Until Phase C the agent image built from a hand-kept mirror in
`NessieAI/docker/cc-runtime/baml_src/`; these tests keep that mirror from coming back
and keep the named context pointed at the canonical tree:

- the canonical tree holds exactly the 8 files, and cc-runtime holds no `.baml` file
- the generated Compose block maps the named context onto the canonical tree
- the Dockerfile's only writer of /app/baml_src/ is the COPY from that named context
- the generator config still lands the judge client where judge_runner imports it
"""
from __future__ import annotations

import posixpath
import re

from NessieAI import paths
from NessieAI.build_tools.gen_op_surfaces.constants import IMAGE_BAML_SRC_PATH
from NessieAI.build_tools.gen_op_surfaces.docker_blocks import validate_baml_context_copy
from NessieAI.tests.router.image_baml import image_baml_dir

CANONICAL = paths.DMAC_ASSISTANT_DIR / "baml_src"
DOCKERFILE = paths.CC_RUNTIME_DIR / "Dockerfile"
JUDGE_RUNNER = paths.CC_RUNTIME_DIR / "tools" / "e2e" / "judge_runner.py"

# Adding or removing a BAML file means editing this tuple, so the change is made
# on purpose.
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
    # listing check would compare an empty list once the root moved.
    assert root.is_dir(), f"BAML tree not found at {root}"
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*.baml"))


def test_canonical_tree_holds_exactly_the_eight_baml_files():
    assert _baml_names(CANONICAL) == sorted(BAML_FILES)


def test_cc_runtime_holds_no_baml_copy():
    """The agent image's build context must not carry BAML sources of its own:
    a copy there is a second tree to keep identical by hand."""
    assert paths.CC_RUNTIME_DIR.is_dir()
    assert not (paths.CC_RUNTIME_DIR / "baml_src").exists()
    strays = sorted(
        p.relative_to(paths.CC_RUNTIME_DIR).as_posix()
        for p in paths.CC_RUNTIME_DIR.rglob("*.baml")
    )
    assert not strays, f"BAML files under the cc-runtime build context: {strays}"


def test_image_baml_context_resolves_to_the_canonical_tree():
    resolved = image_baml_dir()
    assert resolved == CANONICAL.resolve()
    assert _baml_names(resolved) == sorted(BAML_FILES)


def test_dockerfile_copies_baml_only_from_the_named_context():
    validate_baml_context_copy(DOCKERFILE.read_text(encoding="utf-8"))


def test_image_generates_the_judge_client_where_judge_runner_imports_it():
    """The image path of the BAML tree did not change, so `baml-cli generate` and the
    e2e generator's relative output_dir still put the client at /app/tools/e2e/."""
    generators = (CANONICAL / "generators.baml").read_text(encoding="utf-8")
    block = re.search(r"generator\s+e2e_target\s*\{(.*?)\}", generators, re.DOTALL)
    assert block, "generators.baml has no e2e_target generator"
    output_dir = re.search(r'output_dir\s+"([^"]+)"', block.group(1))
    assert output_dir, "e2e_target has no output_dir"
    client_parent = posixpath.normpath(posixpath.join(IMAGE_BAML_SRC_PATH, output_dir.group(1)))
    assert client_parent == "/app/tools/e2e"

    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    assert f"baml-cli generate --from {IMAGE_BAML_SRC_PATH.rstrip('/')} " in dockerfile
    assert "test -d /app/tools/e2e/baml_client" in dockerfile
    assert "from tools.e2e.baml_client import b" in JUDGE_RUNNER.read_text(encoding="utf-8")
