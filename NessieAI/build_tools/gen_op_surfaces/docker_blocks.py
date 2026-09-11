"""Emit and validate Dockerfile plugin COPY/PATH and Compose named-context blocks."""
from __future__ import annotations

import re
from pathlib import Path

from NessieAI.build_tools.gen_op_surfaces.blocks import validate_markers
from NessieAI.build_tools.gen_op_surfaces.constants import (
    ADDITIONAL_CONTEXTS_BEGIN,
    ADDITIONAL_CONTEXTS_END,
    CANONICAL_CAPABILITIES_IN_CONTEXT,
    IMAGE_BAML_SRC_PATH,
    IMAGE_CAPABILITIES_PATH,
    NAMED_BAML_CONTEXT,
    NAMED_BUILD_CONTEXTS,
    NAMED_CAPABILITIES_CONTEXT,
    PLUGINS_ROOT_REL,
)
from NessieAI.cc.op_registry.install_oracle import (
    PLUGIN_COPY_RE,
    PLUGIN_PATH_RE,
    discover_install,
    manifest_plugin_dirs,
)

_PLUGINS_ROOT_REL = Path(PLUGINS_ROOT_REL)
_COPY_RE = re.compile(
    r"^COPY\s+(?P<flags>(?:--\S+\s+)*)(?P<src>\S+)\s+(?P<dest>\S+)\s*$"
)


class CanonicalCapabilitiesError(ValueError):
    """Raised when the in-image capabilities path is not finally written by canonical source."""


class ComposeContextError(ValueError):
    """Raised when a Compose named build context is missing or unsafe."""


class BamlContextError(ValueError):
    """Raised when the image's BAML sources do not come only from the named context."""


def _plugins_root(repo_root: Path) -> Path:
    return repo_root / _PLUGINS_ROOT_REL


def emit_plugin_copy_block(repo_root: Path) -> str:
    """Render one exact per-plugin COPY line for every manifest-bearing plugin."""
    names = manifest_plugin_dirs(_plugins_root(repo_root))
    if not names:
        return ""
    return "".join(
        f"COPY build_context/plugins/{name}/ /app/plugins/{name}/\n" for name in names
    )


def emit_plugin_path_block(repo_root: Path) -> str:
    """Render one PATH entry per plugin, preserving literal ${PATH}."""
    names = manifest_plugin_dirs(_plugins_root(repo_root))
    if not names:
        return ""
    joined = ":".join(f"/app/plugins/{name}/bin" for name in names)
    return f'ENV PATH="{joined}:${{PATH}}"\n'


def emit_capabilities_copy_block(_repo_root: Path) -> str:
    """Copy canonical capabilities.md from the named chat_nextseek context."""
    return (
        f"COPY --from={NAMED_CAPABILITIES_CONTEXT} "
        f"{CANONICAL_CAPABILITIES_IN_CONTEXT} "
        f"{IMAGE_CAPABILITIES_PATH}\n"
    )


def emit_additional_contexts_block(_repo_root: Path) -> str:
    """Declare every named additional build context at its tree."""
    return "      additional_contexts:\n" + "".join(
        f"        {name}: ./{path}\n" for name, path in NAMED_BUILD_CONTEXTS
    )


def parse_plugin_copy_names(text: str) -> set[str]:
    names: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        match = PLUGIN_COPY_RE.match(stripped)
        if match:
            names.add(match.group("plugin"))
    return names


def parse_plugin_path_names(text: str) -> set[str]:
    names: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or not stripped.startswith("ENV PATH="):
            continue
        names.update(PLUGIN_PATH_RE.findall(stripped))
    return names


def four_install_sets(
    *,
    plugins_root: Path,
    dockerfile_path: Path,
) -> tuple[set[str], set[str], set[str], set[str]]:
    """Return (dir discovery, COPY names, oracle installed, PATH names)."""
    discovery = discover_install(
        plugins_root=plugins_root,
        dockerfile_path=dockerfile_path,
    )
    dirs = set(manifest_plugin_dirs(plugins_root))
    copies = {dest.plugin_name for dest in discovery.copy_destinations}
    installed = set(discovery.plugins)
    paths = {entry.plugin_name for entry in discovery.path_entries}
    return dirs, copies, installed, paths


def _from_context(flags: str) -> str | None:
    for token in flags.split():
        if token.startswith("--from="):
            return token[len("--from=") :]
    return None


def _writes_capabilities(dest: str) -> bool:
    if dest.rstrip("/") == IMAGE_CAPABILITIES_PATH.rstrip("/"):
        return True
    if dest.endswith("/") and IMAGE_CAPABILITIES_PATH.startswith(dest):
        return True
    return dest.rstrip("/") == "/app/plugins/nextseek"


def _is_canonical_writer(from_name: str | None, src: str, dest: str) -> bool:
    return (
        from_name == NAMED_CAPABILITIES_CONTEXT
        and src == CANONICAL_CAPABILITIES_IN_CONTEXT
        and dest == IMAGE_CAPABILITIES_PATH
    )


def validate_canonical_capabilities_final_writer(dockerfile_text: str) -> None:
    """Require the named-context COPY to be the last writer of in-image capabilities."""
    writers: list[tuple[str | None, str, str, bool]] = []
    for line in dockerfile_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _COPY_RE.match(stripped)
        if not match:
            continue
        src = match.group("src")
        dest = match.group("dest")
        from_name = _from_context(match.group("flags"))
        if _writes_capabilities(dest):
            writers.append(
                (from_name, src, dest, _is_canonical_writer(from_name, src, dest))
            )
    if not any(canonical for *_, canonical in writers):
        raise CanonicalCapabilitiesError(
            "missing named context COPY of canonical capabilities.md from chat_nextseek"
        )
    last_from, last_src, last_dest, last_canonical = writers[-1]
    if not last_canonical:
        raise CanonicalCapabilitiesError(
            "later overwrite of in-image capabilities path after canonical COPY: "
            f"{last_from} {last_src} {last_dest}"
        )


def validate_compose_named_context(
    *,
    repo_root: Path,
    contexts: dict[str, str],
    name: str = NAMED_CAPABILITIES_CONTEXT,
) -> Path:
    """Require the named context ``name`` to resolve to its tree inside repo_root.

    Returns the resolved tree. ``name`` defaults to the chat_nextseek context.
    """
    expected_paths = dict(NAMED_BUILD_CONTEXTS)
    if name not in expected_paths:
        raise ComposeContextError(f"unknown named context {name}")
    expected_path = expected_paths[name]
    if name not in contexts:
        raise ComposeContextError(f"missing named context {name}")
    raw = contexts[name]
    if not isinstance(raw, str) or not raw.strip():
        raise ComposeContextError(f"named context {name} source is empty")
    path = Path(raw)
    if path.is_absolute() or raw.startswith("/") or raw.startswith("~"):
        raise ComposeContextError(
            f"absolute or external named context is forbidden: {raw}"
        )
    if ".." in path.parts:
        raise ComposeContextError(
            f"named context traversal is forbidden: {raw}"
        )
    expected = (repo_root / expected_path).resolve()
    resolved = (repo_root / raw).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ComposeContextError(
            f"named context resolves outside repository: {raw}"
        ) from exc
    if resolved != expected:
        raise ComposeContextError(
            f"named context does not resolve to the {expected_path} "
            f"tree: {raw} -> {resolved}"
        )
    if not resolved.is_dir():
        raise ComposeContextError(
            f"named context path is not a directory: {resolved}"
        )
    return resolved


def validate_compose_named_contexts(
    *,
    repo_root: Path,
    contexts: dict[str, str],
) -> dict[str, Path]:
    """Require every declared named context to resolve to its tree; return them."""
    return {
        name: validate_compose_named_context(
            repo_root=repo_root, contexts=contexts, name=name
        )
        for name, _ in NAMED_BUILD_CONTEXTS
    }


_CONTEXT_ENTRY_RE = re.compile(r"^(?P<name>[A-Za-z0-9_.-]+):\s+(?P<path>\S+)$")


def parse_additional_contexts_block(compose_text: str) -> dict[str, str]:
    """Return {NAME: PATH} from the generated additional-contexts block.

    Reads only the marked block, so it sees what the generator wrote. Any line
    it does not recognise is refused rather than skipped.
    """
    try:
        validate_markers(compose_text, ADDITIONAL_CONTEXTS_BEGIN, ADDITIONAL_CONTEXTS_END)
    except ValueError as exc:
        raise ComposeContextError(f"additional-contexts block: {exc}") from exc
    start = compose_text.index(ADDITIONAL_CONTEXTS_BEGIN) + len(ADDITIONAL_CONTEXTS_BEGIN)
    body = compose_text[start : compose_text.index(ADDITIONAL_CONTEXTS_END)]
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not lines or lines[0] != "additional_contexts:":
        raise ComposeContextError("additional-contexts block has no additional_contexts key")
    contexts: dict[str, str] = {}
    for line in lines[1:]:
        match = _CONTEXT_ENTRY_RE.match(line)
        if not match:
            raise ComposeContextError(f"unparsed additional-contexts line: {line!r}")
        contexts[match.group("name")] = match.group("path")
    return contexts


def _copy_tokens(line: str) -> tuple[str | None, list[str], str] | None:
    """Split a COPY line into (--from name, sources, destination)."""
    tokens = line.split()
    if len(tokens) < 3 or tokens[0] != "COPY":
        return None
    flags = [token for token in tokens[1:] if token.startswith("--")]
    rest = [token for token in tokens[1:] if not token.startswith("--")]
    if len(rest) < 2:
        return None
    return _from_context(" ".join(flags)), rest[:-1], rest[-1]


def _writes_baml_src(dest: str) -> bool:
    image_dir = IMAGE_BAML_SRC_PATH.rstrip("/")
    return dest.rstrip("/") == image_dir or dest.startswith(image_dir + "/")


def validate_baml_context_copy(dockerfile_text: str) -> None:
    """Require exactly one writer of the in-image BAML tree: the named-context COPY.

    A COPY of BAML sources from the cc-runtime build context itself means the
    hand-kept mirror is back, and the image would generate its client from bytes
    Django does not run.
    """
    writers: list[tuple[str | None, list[str], str]] = []
    for line in dockerfile_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parsed = _copy_tokens(stripped)
        if parsed and _writes_baml_src(parsed[2]):
            writers.append(parsed)
    if not writers:
        raise BamlContextError(
            f"missing named context COPY of the BAML sources from {NAMED_BAML_CONTEXT}"
        )
    if len(writers) > 1:
        raise BamlContextError(
            f"more than one COPY writes {IMAGE_BAML_SRC_PATH}: {writers}"
        )
    from_name, sources, dest = writers[0]
    if from_name != NAMED_BAML_CONTEXT:
        raise BamlContextError(
            f"BAML sources are copied from {from_name or 'the build context'}, "
            f"not the named context {NAMED_BAML_CONTEXT}: {sources} {dest}"
        )
    if sources not in (["."], ["./"]) or dest != IMAGE_BAML_SRC_PATH:
        raise BamlContextError(
            f"the named context COPY must copy the whole tree to {IMAGE_BAML_SRC_PATH}: "
            f"{sources} {dest}"
        )
