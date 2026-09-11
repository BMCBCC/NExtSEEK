"""Shared constants for deterministic surface generation.

Every target is named relative to the checkout root, because the CLI joins it
onto ``--root``. The locations come from ``NessieAI.paths`` so a later move
edits one file; ``repo_relative`` turns each into the repo-relative form.
"""
from __future__ import annotations

from NessieAI import paths

EXIT_NO_CHANGE = 0
EXIT_ERROR = 1
EXIT_CHANGES_WRITTEN = 2

# The Compose named build context the cc-agent Dockerfile COPYs from. The NAME
# is what `COPY --from=` references and never changes; the PATH is where that
# context lives in the checkout.
NAMED_CAPABILITIES_CONTEXT = "chat_nextseek"
NAMED_CAPABILITIES_CONTEXT_PATH = paths.repo_relative(paths.CHAT_NEXTSEEK_DIR)
CANONICAL_CAPABILITIES_IN_CONTEXT = (
    "src/chat_nextseek/context/capabilities.md"
)
IMAGE_CAPABILITIES_PATH = "/app/plugins/nextseek/context/capabilities.md"

# The canonical file is the named context's file, so the two cannot disagree.
CANONICAL_CAPABILITIES_REL = (
    f"{NAMED_CAPABILITIES_CONTEXT_PATH}/{CANONICAL_CAPABILITIES_IN_CONTEXT}"
)
BAKED_CAPABILITIES_REL = paths.repo_relative(
    paths.CC_PLUGIN_DIR / "context" / "capabilities.md"
)
ROUTE_CAPABILITIES_REL = paths.repo_relative(
    paths.DMAC_BUILD_CONTEXT / "route_capabilities.json"
)
PLUGINS_ROOT_REL = paths.repo_relative(paths.CC_PLUGIN_DIR.parent)

COMMAND_OPS_BEGIN = "<!-- BEGIN PLAN005-GEN:command-ops -->"
COMMAND_OPS_END = "<!-- END PLAN005-GEN:command-ops -->"

SKILL_OPS_BEGIN = "<!-- BEGIN PLAN005-GEN:skill-ops -->"
SKILL_OPS_END = "<!-- END PLAN005-GEN:skill-ops -->"

DOCKERFILE_REL = paths.repo_relative(paths.CC_RUNTIME_DIR / "Dockerfile")
COMPOSE_REL = "docker-compose.yml"

PLUGIN_COPY_BEGIN = "# BEGIN PLAN005-GEN:plugin-copy"
PLUGIN_COPY_END = "# END PLAN005-GEN:plugin-copy"
PLUGIN_PATH_BEGIN = "# BEGIN PLAN005-GEN:plugin-path"
PLUGIN_PATH_END = "# END PLAN005-GEN:plugin-path"
CAPABILITIES_COPY_BEGIN = "# BEGIN PLAN005-GEN:capabilities-copy"
CAPABILITIES_COPY_END = "# END PLAN005-GEN:capabilities-copy"
ADDITIONAL_CONTEXTS_BEGIN = "# BEGIN PLAN005-GEN:additional-contexts"
ADDITIONAL_CONTEXTS_END = "# END PLAN005-GEN:additional-contexts"

CLAUDE_MD_REL = paths.repo_relative(paths.CC_RUNTIME_DIR / "container" / "CLAUDE.md")
CONTENT_HASH_REL = paths.repo_relative(
    paths.CC_RUNTIME_DIR / "docs" / "nextseek" / ".content-hash"
)
# The docs snapshot is pinned to a commit that predates the NessieAI move, so
# a `git show <ref>:<path>` against it needs the paths as they were at that
# commit. History, never rewritten.
NEXTSEEK_DOCS_PIN_REF = "a9d69522"
NEXTSEEK_DOCS_PIN_CLAUDE_MD_REL = "docker/cc-runtime/container/CLAUDE.md"
NEXTSEEK_DOCS_PIN_CONTENT_HASH_REL = "docker/cc-runtime/docs/nextseek/.content-hash"

CLAUDE_PLUGINS_BEGIN = "<!-- BEGIN PLAN005-GEN:plugins -->"
CLAUDE_PLUGINS_END = "<!-- END PLAN005-GEN:plugins -->"
CLAUDE_SKILLS_BEGIN = "<!-- BEGIN PLAN005-GEN:skills -->"
CLAUDE_SKILLS_END = "<!-- END PLAN005-GEN:skills -->"
CLAUDE_OPS_BEGIN = "<!-- BEGIN PLAN005-GEN:operations -->"
CLAUDE_OPS_END = "<!-- END PLAN005-GEN:operations -->"

NEXTSEEK_DOCS_BEGIN = "<!-- BEGIN NEXTSEEK-DOCS (auto-generated) -->"
NEXTSEEK_DOCS_END = "<!-- END NEXTSEEK-DOCS (auto-generated) -->"

SKILL_OPS_FIELDS = (
    "op_id",
    "bin_name",
    "purpose",
    "transport",
    "gate_class",
    "availability",
    "per_op_gate_enabled",
)

MARKER_PREFIX = "<!-- BEGIN PLAN005-GEN:"
MARKER_SUFFIX = "-->"

# The Compose named build context the cc-agent Dockerfile COPYs its BAML sources
# from. It is the canonical tree itself, so the image has no BAML copy of its own
# to drift. The image path is unchanged, so `baml-cli generate` and the
# generators' output_dir resolve exactly as they did when the build context held
# a mirror.
NAMED_BAML_CONTEXT = "dmac_assistant_baml"
NAMED_BAML_CONTEXT_PATH = paths.repo_relative(paths.DMAC_ASSISTANT_DIR / "baml_src")
IMAGE_BAML_SRC_PATH = "/app/baml_src/"

# Every named context the cc-agent build declares, as (NAME, PATH), in the order
# the generated Compose block lists them.
NAMED_BUILD_CONTEXTS = (
    (NAMED_CAPABILITIES_CONTEXT, NAMED_CAPABILITIES_CONTEXT_PATH),
    (NAMED_BAML_CONTEXT, NAMED_BAML_CONTEXT_PATH),
)
