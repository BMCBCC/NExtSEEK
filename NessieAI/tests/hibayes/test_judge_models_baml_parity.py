"""`NessieAI/hibayes/judge_models.py` matches `functional_evaluator.baml`.

The judge schema lives in two files that change together (`NessieAI/README.md`
"To change X, edit Y"): the BAML file, which the cc-agent image also builds from
(`NessieAI/tests/router/test_baml_single_source.py`), and the pydantic models here.
A value or field added on one side and not the other only shows up as a validation
error on a paid judge run, so this compares the two sources directly:

- the set of enums and classes the BAML file declares equals `judge_models.__all__`
- every enum's wire values (the `@alias` when there is one), in order
- every class's fields, in order, with their types and optionality
- the `usefulness_score` range, which BAML states only in its `@description`

The BAML file also claims its `FailureMode` wire form equals the exporter's
`FailureMode` values, which `NessieAI/hibayes/enums.py` re-exports; that is checked too.

The parser is deliberately narrow: a BAML line it does not recognise fails the test
rather than being skipped, so a new attribute or type form cannot slip past it.
"""
from __future__ import annotations

import enum
import functools
import re
import types
import typing

import pytest

from NessieAI import paths
from NessieAI.hibayes import exporter, judge_models

BAML = paths.DMAC_ASSISTANT_DIR / "baml_src" / "functional_evaluator.baml"

_COMMENT = re.compile(r"//[^\n]*")
_FIRST_FUNCTION = re.compile(r"^function\s", re.MULTILINE)
_BLOCK = re.compile(r"^(enum|class)\s+(\w+)\s*\{(.*?)^\}", re.MULTILINE | re.DOTALL)
_ENUM_VALUE = re.compile(r'^(\w+)(?:\s+@alias\("([^"]*)"\))?$')
_FIELD = re.compile(r'^(\w+)\s+(\w+)(\?)?(?:\s+@description\("([^"]*)"\))?$')
_RANGE = re.compile(r"^(\d+) to (\d+)\b")
_SCALARS = {"string": str, "int": int, "bool": bool, "float": float}


@functools.lru_cache(maxsize=1)
def _schema():
    """Parse the enum and class blocks into {name: [...]} dicts.

    Enums map to their wire values in declaration order. Classes map to
    (field, base type name, optional, description) tuples in declaration order.
    Everything from the first `function` on is the prompt, so it is cut off.
    """
    assert BAML.is_file(), f"BAML judge schema not found at {BAML}"
    text = _COMMENT.sub("", BAML.read_text(encoding="utf-8"))
    match = _FIRST_FUNCTION.search(text)
    if match:
        text = text[: match.start()]
    enums, classes = {}, {}
    for kind, name, body in _BLOCK.findall(text):
        lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        if kind == "enum":
            values = []
            for ln in lines:
                if ln == "@@dynamic":
                    continue
                m = _ENUM_VALUE.match(ln)
                assert m, f"enum {name}: unparsed BAML line {ln!r}"
                values.append(m.group(2) if m.group(2) is not None else m.group(1))
            enums[name] = values
        else:
            fields = []
            for ln in lines:
                m = _FIELD.match(ln)
                assert m, f"class {name}: unparsed BAML line {ln!r}"
                fields.append((m.group(1), m.group(2), m.group(3) == "?", m.group(4)))
            classes[name] = fields
    assert enums and classes, f"no enum or class blocks parsed from {BAML}"
    return enums, classes


def _python_type(annotation):
    """Return (base type, optional) for a resolved pydantic field annotation."""
    if typing.get_origin(annotation) in (typing.Union, types.UnionType):
        args = typing.get_args(annotation)
        rest = tuple(a for a in args if a is not type(None))
        assert len(rest) == 1, f"unsupported union annotation {annotation!r}"
        return rest[0], len(rest) != len(args)
    return annotation, False


def _bounds(field_info):
    ge = le = None
    for item in field_info.metadata:
        ge = getattr(item, "ge", ge)
        le = getattr(item, "le", le)
    return ge, le


def _python_enums():
    return sorted(
        name for name in judge_models.__all__
        if issubclass(getattr(judge_models, name), enum.Enum)
    )


def _python_models():
    return sorted(
        name for name in judge_models.__all__
        if not issubclass(getattr(judge_models, name), enum.Enum)
    )


def test_baml_declares_exactly_the_names_judge_models_exports():
    enums, classes = _schema()
    assert sorted(enums) == _python_enums()
    assert sorted(classes) == _python_models()


@pytest.mark.parametrize("name", _python_enums())
def test_enum_wire_values_match(name):
    enums, _ = _schema()
    assert name in enums, f"{name} is in judge_models but not declared in {BAML.name}"
    python_values = [member.value for member in getattr(judge_models, name)]
    assert python_values == enums[name]


@pytest.mark.parametrize("name", _python_models())
def test_class_fields_match_in_order_type_and_optionality(name):
    _, classes = _schema()
    assert name in classes, f"{name} is in judge_models but not declared in {BAML.name}"
    model_fields = getattr(judge_models, name).model_fields
    assert list(model_fields) == [field for field, _, _, _ in classes[name]]
    for field, baml_type, optional, _ in classes[name]:
        expected = _SCALARS.get(baml_type) or getattr(judge_models, baml_type, None)
        assert expected is not None, f"{name}.{field}: unknown BAML type {baml_type!r}"
        actual = _python_type(model_fields[field].annotation)
        assert actual == (expected, optional), f"{name}.{field}"


@pytest.mark.parametrize("name", _python_models())
def test_numeric_ranges_match_the_baml_descriptions(name):
    """A BAML description that opens with "N to M" is the field's range; the
    pydantic field must carry exactly ge=N, le=M, and no field may carry a bound
    the BAML side does not state."""
    _, classes = _schema()
    model_fields = getattr(judge_models, name).model_fields
    for field, _, _, description in classes[name]:
        m = _RANGE.match(description or "")
        expected = (int(m.group(1)), int(m.group(2))) if m else (None, None)
        assert _bounds(model_fields[field]) == expected, f"{name}.{field}"


def test_usefulness_score_range_is_parsed_from_the_baml_file():
    """Guards the range check above against passing vacuously: the one ranged
    field today must be found on both sides."""
    _, classes = _schema()
    descriptions = {field: d for field, _, _, d in classes["FunctionalEvaluation"]}
    assert _RANGE.match(descriptions["usefulness_score"] or "")
    assert _bounds(judge_models.FunctionalEvaluation.model_fields["usefulness_score"]) == (0, 4)


def test_exporter_failure_mode_matches_the_baml_wire_values():
    enums, _ = _schema()
    assert [member.value for member in exporter.FailureMode] == enums["FailureMode"]
