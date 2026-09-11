"""No-stack tests for the Nessie lane: its selection switches and its pure helpers.

Stack-free by design, like the other *_unit.py files: no network, no credentials,
no browser.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ci.smoke.conftest import nessie_skip_reason


@pytest.mark.parametrize("keywords, no_nessie, no_turns, expected", [
    ({"test_x"}, True, True, None),                               # not a Nessie test
    ({"nessie"}, False, False, None),                             # the lane runs
    ({"nessie"}, True, False, "Nessie lane skipped by --no-nessie"),
    ({"nessie", "nessie_turn"}, True, True, "Nessie lane skipped by --no-nessie"),
    ({"nessie", "nessie_turn"}, False, True, "chat turns skipped by --nessie-no-turns"),
    ({"nessie"}, False, True, None),                              # stage 1 still runs
])
def test_nessie_skip_reason(keywords, no_nessie, no_turns, expected):
    assert nessie_skip_reason(keywords, no_nessie=no_nessie, no_turns=no_turns) == expected


def test_the_nessie_switch_is_not_a_mark_expression():
    """-m re-admits the write lane; the Nessie switch must never need one."""
    import ci.smoke.conftest as conftest
    source = Path(conftest.__file__).read_text()
    gate = source.index("def pytest_collection_modifyitems")
    early_return = source.index('if config.getoption("-m"):', gate)
    nessie_gate = source.index("nessie_skip_reason(", gate)
    assert nessie_gate < early_return, (
        "the Nessie gate must run before the -m early return, or --no-nessie "
        "stops working whenever someone passes -m"
    )
