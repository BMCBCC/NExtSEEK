from pathlib import Path

from NessieAI.tests import e2e as e2e_pkg


def test_e2e_dsl_and_catalog_load():
    from NessieAI.tests.e2e.catalog import load_catalog, Catalog, Variant, Turn, PassCriterion  # noqa
    cat_path = Path(e2e_pkg.__file__).resolve().parent / "catalog.json"
    cat = load_catalog(cat_path)
    assert isinstance(cat, Catalog)
    assert len(cat.families) == 11
    total = sum(len(f.variants) for f in cat.families.values())
    assert total >= 300
