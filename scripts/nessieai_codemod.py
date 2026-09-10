#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["libcst>=1.1,<2"]
# ///
"""Point Python imports and dotted module strings at the NessieAI/ layout.

This is the codemod of the NessieAI consolidation, Phase A, commit C4. The
move itself (commit C1) was pure ``git mv``; this script rewrites the code that
names the moved modules. It is committed so that an in-flight branch can be
rebased onto the move and then re-run through the same map:

    git rebase origin/dev
    uv run scripts/nessieai_codemod.py            # rewrite in place
    uv run scripts/nessieai_codemod.py --check    # exit 1 if anything is left

What it rewrites, across every tracked ``*.py`` file except NessieAI/history/
(frozen records) and this file:

* ``import a.b.c`` and ``from a.b import x, y`` statements. A ``from`` import
  whose names now live in different packages is split into one statement per
  package, and a name whose last segment changed keeps its binding with
  ``as <old name>``.
* Dotted module names inside string literals and comments (mock.patch targets,
  importlib and importorskip names, logger names, ``-m`` arguments, argparse
  ``prog`` strings, docstrings). A dotted name counts only when it is not
  preceded by a word character, a dot, ``-``, ``/`` or ``\\``, and the
  ``e2e`` root counts only at the very start of a string, so that
  ``tools.e2e`` (the cc-runtime package) and paths such as
  ``chat_frontend/e2e`` are never touched. Names ending in a file extension
  (``e2e.py``) are left alone. Single-segment names are never rewritten.

What it deliberately leaves alone:

* ``chat_nextseek`` and ``dmac_assistant``: editable dists whose import names
  did not change.
* The API shell that stays in nextseek_api: the ``cc_assistant`` Django app
  (its package name, ``apps``, ``cc_sweep``, ``cc_upload_tasks``,
  ``cc_endpoint_guards``), every other ``nextseek_api/assistant`` module
  (``models_db``, ``consumers``, ``session_debug`` ...), ``nextseek_api/services``
  and ``nextseek_api/tests`` apart from the AI tests that moved.
* A reference to a module that still exists at its old path (a real ``.py``
  file or a package with ``__init__.py``) is kept and reported, because the
  module has not moved yet. On a rebased branch this is how a new file that git
  left at an old location shows up: move it, then run the codemod again.
* References to modules that moved into NessieAI/history/ are kept and
  reported: history is not importable.
* In a file that registers e2e modules in ``sys.modules`` by hand (import
  stubs, purges of a poisoned entry), no e2e string is rewritten and each one
  is reported. Such a file also names the bare ``e2e`` package key, which a
  dotted-name rewrite cannot map; renaming only its dotted keys would install
  the stubs under the real package name and shadow it for every test
  collected afterwards. Those files are fixed by hand, all keys at once.
* Relative imports are never rewritten; one whose target does not exist on
  disk is reported.
* File paths (``nextseek_api/eval/...`` joins, ``parents[N]`` anchors) are not
  module names; commit C5 fixes those by hand.

The report lists every kept, archived, missing or unresolved reference, so a
re-run on another branch says exactly what still needs a human.
"""
from __future__ import annotations

import argparse
import difflib
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

# ---------------------------------------------------------------------------
# The map.
#
# Module names are written with "/" between segments so that this file never
# matches the tree-wide greps that look for the old dotted names.
#
#   kind    prefix : the rule applies to the name and to everything below it
#           exact  : the rule applies to exactly this name
#           child  : the rule applies to everything strictly below this name
#   new     a module path, "keep" (stays where it is) or "history" (archived)
#
# "{a,b,c}" in the last old segment expands to one rule per name, and "{}" in
# the new column stands for that name. Lookup is most-specific first: the
# longest matching old prefix wins, and at equal length exact beats prefix
# beats child.
# ---------------------------------------------------------------------------
RULES = """
# Container-CC. The Django shell stays in nextseek_api: INSTALLED_APPS names the
# package, and the Celery task names live in cc_sweep and cc_upload_tasks.
exact   nextseek_api/cc_assistant                                       keep
prefix  nextseek_api/cc_assistant/{apps,cc_sweep,cc_upload_tasks,cc_endpoint_guards}  keep

# The top-level router and its posterior-routing and telemetry consumers.
prefix  nextseek_api/cc_assistant/{router,router_context,posterior_selector,family_labels,baml_introspect,transport_trace,risk_overlay,route_monitoring,turn_ledger}  NessieAI/router/{}

# Gate tooling with no runtime importer, and the operator-run gate scripts.
prefix  nextseek_api/cc_assistant/{step7_gate_catalog,step7_per_op_evidence,bin_inventory}  NessieAI/tests/cc/{}
prefix  nextseek_api/cc_assistant/scripts                               NessieAI/tests/cc/scripts
prefix  nextseek_api/cc_assistant/scripts/{extract_step7_upstream_catalog,verify_merge_survivals}  history
prefix  nextseek_api/cc_assistant/{archive,evidence,acceptance_evidence}  history

# The CC op contract, then every other engine module of the package.
prefix  nextseek_api/cc_assistant/op_registry                           NessieAI/cc/op_registry
child   nextseek_api/cc_assistant                                       NessieAI/cc

# cc_assistant/tests: most go to tests/cc; router, HiBayes and infra tests
# were misfiled there and go where their subject lives.
prefix  nextseek_api/cc_assistant/tests                                 NessieAI/tests/cc
prefix  nextseek_api/cc_assistant/tests/live_evidence                   history
prefix  nextseek_api/cc_assistant/tests/{test_agent_history_conversion,test_baml_router_schema,test_decide_route_pipeline_gate,test_decide_route_sticky_cc,test_f_constraint_pins,test_posterior_selector,test_risk_overlay,test_route_override,test_router_context,test_router_family,test_router_heuristic,test_router_history_plumbing,test_router_ledger_v46,test_router_v46_calltable,test_router_v46_mutations,test_runtime_p0,test_turn_ledger_model,test_turn_ledger_writer,test_v4_2_force_route_http,test_v4_2_product_mutations,test_v4_7_route_monitoring}  NessieAI/tests/router/{}
prefix  nextseek_api/cc_assistant/tests/{generation_test_factory,test_eval_export,test_eval_publish,test_eval_vendoring,test_generation_store_validation,test_judge_cache,test_run_authorization,test_v4_8_gate,test_v4_8_mutations,test_v4_8_reconciliation,test_v4_8_reserve,test_v4_8_resume}  NessieAI/tests/hibayes/{}
prefix  nextseek_api/cc_assistant/tests/{test_build_context_env_guard,test_compose_db_healthcheck,test_django_debug_env,test_entrypoint_attribute_runtimes,test_entrypoint_migrate_failfast,test_issue_conventions_guard,test_validate_issue}  nextseek_api/tests/repo_guards/{}

# HiBayes (the eval package, renamed to its role) and the agent-facing schema RAG.
prefix  nextseek_api/eval                                               NessieAI/hibayes
prefix  nextseek_api/eval/tests                                         NessieAI/tests/hibayes
prefix  nextseek_api/schema_rag                                         NessieAI/schema_rag
prefix  nextseek_api/schema_rag/tests                                   NessieAI/tests/schema_rag

# The NS engine half of nextseek_api/assistant. Every other module there stays.
prefix  nextseek_api/assistant/{granular,write_gate,reingest_qa,upload_workbook,bundle_download,debug_projection}  NessieAI/ns/{}
prefix  nextseek_api/assistant/task6_app                                NessieAI/hibayes/task6_app
prefix  nextseek_api/assistant/tests                                    NessieAI/tests/api
prefix  nextseek_api/assistant/tests/{test_build_upload_xlsx_op,test_bundle_download,test_debug_projection,test_file_artifacts,test_granular_artifacts,test_granular_dispatch,test_granular_endpoints,test_granular_models,test_granular_realstack,test_granular_write_gate,test_reingest_qa,test_run_ls_op,test_upload_workbook}  NessieAI/tests/ns/{}
prefix  nextseek_api/assistant/tests/test_route_capabilities            NessieAI/tests/router/test_route_capabilities
prefix  nextseek_api/assistant/tests/acceptance_evidence                history

# AI tests that left the core nextseek_api/tests directory.
prefix  nextseek_api/tests/{test_assistant_unit,test_services_assistant,test_evaluator_integration,test_evaluator_listing,test_evaluator_models,test_evaluator_normalization,test_evaluator_retry,test_ws_origin}  NessieAI/tests/api/{}
prefix  nextseek_api/tests/{test_schema_processor,test_schema_processor_coverage,test_schema_rag_errors,test_schema_rag_ingest_coverage,test_schema_rag_integration,test_schema_rag_retrieve_coverage,test_schema_rag_self_ingest,test_schema_rag_service_coverage,test_schema_rag_session_coverage,test_schema_rag_unit,test_services_schema_rag_coverage}  NessieAI/tests/schema_rag/{}

# The router-aware harness, the e2e test DSL (was chat_nextseek/e2e) and the
# CC surface generators. The Plan 005 closeout protocol went to history.
prefix  nessie_tests                                                    NessieAI/tests/nessie_tests
prefix  e2e                                                             NessieAI/tests/e2e
prefix  e2e/archive                                                     history
prefix  build_tools                                                     NessieAI/build_tools
prefix  build_tools/tests                                               NessieAI/tests/build_tools
prefix  build_tools/{plan005_baseline,plan005_closeout,plan005_closeout_control,plan005_gate,plan005_record,plan005_signoffs,schemas}  history
prefix  build_tools/tests/{test_plan005_baseline,test_plan005_closeout,test_plan005_contract,test_plan005_gate,test_plan005_record}  history
"""

# Roots the map can touch, and where a dotted name with that root counts inside
# a string or comment. "anywhere" = the anchoring described in the docstring;
# "string-start" = only as the first characters of a string literal.
ROOTS = {
    "nextseek_api": "anywhere",
    "nessie_tests": "anywhere",
    "build_tools": "anywhere",
    "e2e": "string-start",
}

# Where a root's OLD modules were importable from, relative to the repo root.
# The e2e DSL sat under chat_nextseek/ (put on sys.path by a helper).
OLD_IMPORT_ROOTS = {"e2e": ("", "chat_nextseek")}

KEEP = ("keep",)
HISTORY = ("history",)

FILE_EXTS = frozenset(
    "py pyc pyi json jsonl md txt sh yml yaml toml csv tsv html log cfg ini mjs js ts tsx "
    "xlsx zst gz tar sql png svg baml".split()
)

CHAIN_RE = re.compile(r"(?<![\w.\-/\\])[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+")

SELF = "scripts/nessieai_codemod.py"
FROZEN_PREFIXES = ("NessieAI/history/",)


def _parse_rules(text: str) -> dict[str, dict[tuple[str, ...], tuple[str, ...]]]:
    tables: dict[str, dict[tuple[str, ...], tuple[str, ...]]] = {"exact": {}, "prefix": {}, "child": {}}
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        kind, old, new = line.split()
        if kind not in tables:
            raise ValueError(f"unknown rule kind {kind!r} in {raw!r}")
        head, _, last = old.rpartition("/")
        if last.startswith("{") and last.endswith("}"):
            names = last[1:-1].split(",")
            olds = [f"{head}/{n}" for n in names]
            news = [new.replace("{}", n) for n in names]
        else:
            if "{}" in new:
                raise ValueError(f"'{{}}' without a group in {raw!r}")
            olds, news = [old], [new]
        for o, n in zip(olds, news):
            key = tuple(o.split("/"))
            value = KEEP if n == "keep" else HISTORY if n == "history" else tuple(n.split("/"))
            if key in tables[kind]:
                raise ValueError(f"duplicate {kind} rule for {o}")
            tables[kind][key] = value
    return tables


TABLES = _parse_rules(RULES)


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Hit:
    value: tuple[str, ...]
    key_len: int  # old segments the matching rule names
    child: bool   # a child rule: the first segment below the key is part of the module

    @property
    def module_len(self) -> int:
        return self.key_len + (1 if self.child else 0)


def lookup(parts: tuple[str, ...]) -> Hit | None:
    """Most-specific rule for a dotted name, or None when no rule applies."""
    for i in range(len(parts), 0, -1):
        key = parts[:i]
        if i == len(parts) and key in TABLES["exact"]:
            return Hit(TABLES["exact"][key], i, False)
        if key in TABLES["prefix"]:
            return Hit(TABLES["prefix"][key], i, False)
        if i < len(parts) and key in TABLES["child"]:
            return Hit(TABLES["child"][key], i, True)
    return None


def map_name(parts: tuple[str, ...]) -> tuple[str, ...]:
    """The pure map with no filesystem checks: the new dotted name (or the same one)."""
    hit = lookup(parts)
    if hit is None or hit.value in (KEEP, HISTORY):
        return parts
    return hit.value + parts[hit.key_len:]


def _is_real_module(base: Path, parts: tuple[str, ...]) -> bool:
    target = base.joinpath(*parts)
    return target.with_suffix(".py").is_file() or (target / "__init__.py").is_file()


def _real_prefix_len(root: Path, parts: tuple[str, ...], import_roots: tuple[str, ...] = ("",)) -> int:
    """Length of the longest prefix of parts that is a real module under root."""
    best = 0
    for sub in import_roots:
        base = root / sub if sub else root
        for i in range(len(parts), 0, -1):
            if i <= best:
                break
            if _is_real_module(base, parts[:i]):
                best = i
                break
    return best


# ---------------------------------------------------------------------------
# Per-file rewriting
# ---------------------------------------------------------------------------
@dataclass
class Note:
    kind: str  # kept | history | missing | relative | unaliased
    path: str
    line: int
    detail: str


@dataclass
class FileResult:
    path: str
    changed: bool = False
    counts: Counter = field(default_factory=Counter)
    notes: list[Note] = field(default_factory=list)
    error: str | None = None
    skipped: str | None = None
    diff: str = ""


class Mapper:
    """The map plus the filesystem guards, recording what it did for one file."""

    def __init__(self, root: Path, result: FileResult, hand_roots: frozenset[str] = frozenset()) -> None:
        self.root = root
        self.result = result
        # string-start roots whose module names this file registers in
        # sys.modules by hand: its strings for that root are left alone.
        self.hand_roots = hand_roots

    def note(self, kind: str, line: int, detail: str) -> None:
        self.result.notes.append(Note(kind, self.result.path, line, detail))

    def map(self, parts: tuple[str, ...], line: int, *, is_module: bool) -> tuple[str, ...] | None:
        """New name for a dotted reference, or None to leave it as it is.

        is_module: the whole name is a module (an import); otherwise the tail
        may be attributes (a mock.patch target, a logger name ...).
        """
        hit = lookup(parts)
        if hit is None or hit.value == KEEP:
            return None
        dotted = ".".join(parts)
        if hit.value == HISTORY:
            self.note("history", line, f"{dotted} moved into NessieAI/history (not importable); left as is")
            return None
        import_roots = OLD_IMPORT_ROOTS.get(parts[0], ("",))
        if _real_prefix_len(self.root, parts, import_roots) >= hit.module_len:
            self.note("kept", line, f"{dotted} still exists at its old path; left as is")
            return None
        new = hit.value + parts[hit.key_len:]
        need = len(new) if is_module else len(hit.value) + (1 if hit.child else 0)
        if _real_prefix_len(self.root, new) < need:
            self.note("missing", line, f"{dotted} -> {'.'.join(new)}: target module not found on disk")
        return new

    def rewrite_text(self, text: str, line: int, *, string_start: bool, counter: str) -> str:
        def repl(m: re.Match[str]) -> str:
            chain = m.group(0)
            parts = tuple(chain.split("."))
            anchor = ROOTS.get(parts[0])
            if anchor is None:
                return chain
            if anchor == "string-start" and not (string_start and m.start() == 0):
                return chain
            if parts[-1] in FILE_EXTS:
                return chain
            if parts[0] in self.hand_roots:
                self.note(
                    "handfix", line,
                    f"{chain}: this file registers {parts[0]} modules in sys.modules by hand; left for a hand fix",
                )
                return chain
            new = self.map(parts, line, is_module=False)
            if new is None:
                return chain
            self.result.counts[counter] += 1
            return ".".join(new)

        return CHAIN_RE.sub(repl, text)


def _dotted(node: cst.BaseExpression | None) -> str | None:
    if node is None:
        return None
    if isinstance(node, cst.Name):
        return node.value
    if isinstance(node, cst.Attribute):
        head = _dotted(node.value)
        return None if head is None else f"{head}.{node.attr.value}"
    return None


def _expr(dotted: str) -> cst.BaseExpression:
    return cst.parse_expression(dotted)


class _UnaliasedImports(cst.CSTVisitor):
    """Pre-pass: `import a.b.c` (no alias) statements whose module moves.

    Such a statement binds the root name `a`, so the code that spells
    `a.b.c.x` has to follow the rewrite.
    """

    def __init__(self, root: Path, rel: str) -> None:
        # A scratch result: the Rewriter records the notes for these imports.
        self.mapper = Mapper(root, FileResult(rel))
        self.moves: dict[str, str] = {}

    def visit_Import(self, node: cst.Import) -> None:
        for alias in node.names:
            if alias.asname is None:
                name = _dotted(alias.name)
                if name is None:
                    continue
                new = self.mapper.map(tuple(name.split(".")), 0, is_module=True)
                if new is not None:
                    self.moves[name] = ".".join(new)


class Rewriter(cst.CSTTransformer):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, mapper: Mapper, file_path: Path, unaliased: dict[str, str]) -> None:
        super().__init__()
        self.mapper = mapper
        self.file_path = file_path
        self.unaliased = unaliased
        self.import_depth = 0
        self.fstring_first_part: set[int] = set()

    # -- helpers --------------------------------------------------------------
    def _line(self, node: cst.CSTNode) -> int:
        try:
            return self.get_metadata(PositionProvider, node).start.line
        except KeyError:
            return 0

    # -- import statements ------------------------------------------------------
    def visit_Import(self, node: cst.Import) -> None:
        self.import_depth += 1

    def leave_Import(self, original: cst.Import, updated: cst.Import) -> cst.Import:
        self.import_depth -= 1
        line = self._line(original)
        names = []
        changed = False
        for alias in updated.names:
            name = _dotted(alias.name)
            new = None if name is None else self.mapper.map(tuple(name.split(".")), line, is_module=True)
            if new is not None:
                changed = True
                self.mapper.result.counts["import"] += 1
                if alias.asname is None:
                    self.mapper.note("unaliased", line, f"import {name} -> import {'.'.join(new)} (uses of {name}.* rewritten)")
                alias = alias.with_changes(name=_expr(".".join(new)))
            names.append(alias)
        return updated.with_changes(names=names) if changed else updated

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        self.import_depth += 1

    def leave_ImportFrom(self, original: cst.ImportFrom, updated: cst.ImportFrom) -> cst.ImportFrom:
        self.import_depth -= 1
        if original.relative:
            self._check_relative(original)
        return updated

    def _check_relative(self, node: cst.ImportFrom) -> None:
        base = self.file_path.parent
        for _ in range(len(node.relative) - 1):
            base = base.parent
        mod = _dotted(node.module) if node.module is not None else None
        target = base.joinpath(*mod.split(".")) if mod else base
        ok = target.with_suffix(".py").is_file() or (target / "__init__.py").is_file()
        if not ok and mod is None:
            ok = target.is_dir()
        if not ok:
            dots = "." * len(node.relative)
            self.mapper.note("relative", self._line(node), f"from {dots}{mod or ''} import ...: target not found on disk")

    def _split_from(self, node: cst.ImportFrom, line: int) -> list[cst.ImportFrom] | None:
        """Rewrite one absolute `from` import; None when nothing changes."""
        if node.relative or node.module is None:
            return None
        module = _dotted(node.module)
        if module is None:
            return None
        mod_parts = tuple(module.split("."))
        if isinstance(node.names, cst.ImportStar):
            new = self.mapper.map(mod_parts, line, is_module=True)
            if new is None:
                return None
            self.mapper.result.counts["import"] += 1
            return [node.with_changes(module=_expr(".".join(new)))]

        groups: dict[str, list[cst.ImportAlias]] = {}
        changed = False
        for alias in node.names:
            name = alias.name.value if isinstance(alias.name, cst.Name) else _dotted(alias.name)
            full = mod_parts + (name,)
            new = self.mapper.map(full, line, is_module=False)
            if new is None:
                new_mod, new_name = module, name
            else:
                new_mod, new_name = ".".join(new[:-1]), new[-1]
                if (new_mod, new_name) != (module, name):
                    changed = True
            if new_name != name:
                asname = alias.asname or cst.AsName(name=cst.Name(name))
                alias = alias.with_changes(name=cst.Name(new_name), asname=asname)
            groups.setdefault(new_mod, []).append(alias)
        if not changed:
            return None
        self.mapper.result.counts["import"] += 1
        for new_mod in groups:
            if new_mod != module and _real_prefix_len(self.mapper.root, tuple(new_mod.split("."))) < len(new_mod.split(".")):
                self.mapper.note("missing", line, f"from {module} import ... -> from {new_mod}: module not found on disk")

        last_comma = node.names[-1].comma
        out = []
        for new_mod, aliases in groups.items():
            aliases = list(aliases)
            tail = last_comma if node.lpar is not None else cst.MaybeSentinel.DEFAULT
            aliases[-1] = aliases[-1].with_changes(comma=tail)
            out.append(node.with_changes(module=_expr(new_mod), names=aliases))
        return out

    def _rewrite_small(self, body, line: int):
        new_body = []
        changed = False
        for stmt in body:
            if isinstance(stmt, cst.ImportFrom):
                repl = self._split_from(stmt, line)
                if repl is not None:
                    new_body.extend(repl)
                    changed = True
                    continue
            new_body.append(stmt)
        return new_body, changed

    def leave_SimpleStatementLine(self, original, updated):
        body, changed = self._rewrite_small(updated.body, self._line(original))
        if not changed:
            return updated
        if len(updated.body) == 1 and len(body) > 1:
            lines = []
            for i, stmt in enumerate(body):
                lines.append(
                    updated.with_changes(
                        body=[stmt],
                        leading_lines=updated.leading_lines if i == 0 else [],
                    )
                )
            return cst.FlattenSentinel(lines)
        return updated.with_changes(body=body)

    def leave_SimpleStatementSuite(self, original, updated):
        body, changed = self._rewrite_small(updated.body, self._line(original))
        return updated.with_changes(body=body) if changed else updated

    # -- code that spells a moved module through an unaliased import -----------
    def leave_Attribute(self, original: cst.Attribute, updated: cst.Attribute) -> cst.BaseExpression:
        if self.import_depth or not self.unaliased:
            return updated
        dotted = _dotted(updated)
        if dotted is None:
            return updated
        for old, new in self.unaliased.items():
            if dotted == old or dotted.startswith(old + "."):
                self.mapper.result.counts["usage"] += 1
                return _expr(new + dotted[len(old):])
        return updated

    # -- strings and comments ---------------------------------------------------
    def visit_FormattedString(self, node: cst.FormattedString) -> None:
        if node.parts and isinstance(node.parts[0], cst.FormattedStringText):
            self.fstring_first_part.add(id(node.parts[0]))

    def leave_FormattedStringText(self, original, updated):
        start = id(original) in self.fstring_first_part
        text = self.mapper.rewrite_text(updated.value, self._line(original), string_start=start, counter="string")
        return updated.with_changes(value=text) if text != updated.value else updated

    def leave_SimpleString(self, original: cst.SimpleString, updated: cst.SimpleString) -> cst.SimpleString:
        value = updated.value
        i = 0
        while value[i] not in "'\"":
            i += 1
        prefix = value[:i]
        if "b" in prefix.lower():
            return updated
        quote = value[i : i + 3] if value[i : i + 3] in ('"""', "'''") else value[i]
        body = value[i + len(quote) : len(value) - len(quote)]
        new_body = self.mapper.rewrite_text(body, self._line(original), string_start=True, counter="string")
        if new_body == body:
            return updated
        return updated.with_changes(value=prefix + quote + new_body + quote)

    def leave_Comment(self, original: cst.Comment, updated: cst.Comment) -> cst.Comment:
        text = self.mapper.rewrite_text(updated.value, self._line(original), string_start=False, counter="comment")
        return updated.with_changes(value=text) if text != updated.value else updated


def rewrite_file(root: Path, rel: str, *, write: bool, want_diff: bool) -> FileResult:
    result = FileResult(rel)
    path = root / rel
    source = path.read_bytes()
    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError as exc:
        text = source.decode("utf-8", errors="replace")
        names_a_root = any(
            m.group(0).split(".")[0] in ROOTS for m in CHAIN_RE.finditer(text)
        ) or re.search(r"^\s*(from|import)\s+(%s)\b" % "|".join(ROOTS), text, re.M)
        first = str(exc).splitlines()[0]
        if names_a_root:
            result.error = f"parse error: {first}"
        else:
            result.skipped = f"parse error, but it names no mapped module: {first}"
        return result
    text = source.decode(module.encoding, errors="replace")
    hand_roots = frozenset(
        r for r, anchor in ROOTS.items()
        if anchor == "string-start"
        and "sys.modules" in text
        and re.search(r"[\"']%s[.\"']" % re.escape(r), text)
    )
    mapper = Mapper(root, result, hand_roots)
    pre = _UnaliasedImports(root, rel)
    module.visit(pre)
    wrapper = MetadataWrapper(module)
    new_module = wrapper.visit(Rewriter(mapper, path, pre.moves))
    new_source = new_module.bytes
    if new_source != source:
        result.changed = True
        if want_diff:
            old_text = source.decode(module.encoding, errors="replace").splitlines(keepends=True)
            new_text = new_source.decode(module.encoding, errors="replace").splitlines(keepends=True)
            result.diff = "".join(difflib.unified_diff(old_text, new_text, f"a/{rel}", f"b/{rel}"))
        if write:
            path.write_bytes(new_source)
    return result


def tracked_python_files(root: Path) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--", "*.py"],
        check=True, capture_output=True,
    ).stdout.decode()
    files = [f for f in out.split("\0") if f]
    return sorted(
        f for f in files
        if f != SELF and not f.startswith(FROZEN_PREFIXES) and (root / f).is_file()
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="nessieai_codemod",
        description="Rewrite imports and dotted module strings for the NessieAI/ move (Phase A, C4).",
    )
    ap.add_argument("--root", default=".", help="repo root (default: current directory)")
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 if any file would change")
    ap.add_argument("--diff", action="store_true", help="print a unified diff of every change")
    ap.add_argument("--list-rules", action="store_true", help="print the expanded map and exit")
    ap.add_argument("paths", nargs="*", help="limit to these repo-relative files (default: every tracked *.py)")
    args = ap.parse_args(argv)

    if args.list_rules:
        for kind in ("exact", "prefix", "child"):
            for key, value in sorted(TABLES[kind].items()):
                print(f"{kind:6}  {'.'.join(key):70}  {'.'.join(value)}")
        return 0

    root = Path(args.root).resolve()
    files = args.paths or tracked_python_files(root)
    results = [rewrite_file(root, f, write=not args.check, want_diff=args.diff) for f in files]

    changed = [r for r in results if r.changed]
    errors = [r for r in results if r.error]
    skipped = [r for r in results if r.skipped]
    totals: Counter = Counter()
    for r in results:
        totals.update(r.counts)
    if args.diff:
        for r in changed:
            sys.stdout.write(r.diff)

    verb = "would change" if args.check else "changed"
    print(
        f"nessieai_codemod: {len(files)} files scanned, {len(changed)} {verb} "
        f"(imports {totals['import']}, strings {totals['string']}, comments {totals['comment']}, "
        f"attribute uses {totals['usage']}), {len(errors)} not parsed, {len(skipped)} skipped",
        file=sys.stderr,
    )
    for r in errors:
        print(f"  not parsed: {r.path}: {r.error}", file=sys.stderr)
    for r in skipped:
        print(f"  skipped: {r.path}: {r.skipped}", file=sys.stderr)
    by_kind: dict[str, list[Note]] = defaultdict(list)
    for r in results:
        for n in r.notes:
            by_kind[n.kind].append(n)
    headings = {
        "kept": "kept: the module still exists at its old path (move it, then re-run)",
        "history": "kept: the module now lives under NessieAI/history (not importable)",
        "missing": "rewritten, but the new target was not found on disk",
        "handfix": "kept: string names in a file that registers those modules in sys.modules by hand",
        "relative": "relative import whose target does not exist",
        "unaliased": "unaliased import rewritten together with its attribute uses (review)",
    }
    for kind, heading in headings.items():
        notes = by_kind.get(kind)
        if not notes:
            continue
        print(f"{heading}: {len(notes)}", file=sys.stderr)
        for n in notes:
            print(f"  {n.path}:{n.line}: {n.detail}", file=sys.stderr)
    if errors:
        return 2
    return 1 if (args.check and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
