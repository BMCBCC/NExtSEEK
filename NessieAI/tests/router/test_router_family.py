"""Task 3 / V4-6: dynamic classifier labels from corpus families."""
import hashlib

from NessieAI import paths
from NessieAI.router.baml_introspect import declared_family_members
from NessieAI.router.family_labels import corpus_snapshot, declared_labels, type_builder
from NessieAI.tests.router.image_baml import image_baml_source

_A = paths.DMAC_ASSISTANT_DIR / "baml_src" / "router.baml"


def test_classification_contract_in_classifier_baml():
    path = paths.DMAC_ASSISTANT_DIR / "baml_src" / "classifier.baml"
    text = path.read_text()
    assert "enum ClassifiedFamily" in text
    assert "@@dynamic" in text
    assert "function ClassifyQuery" in text


def test_both_router_baml_copies_stay_byte_identical():
    """Django and the agent image read one router.baml."""
    _b = image_baml_source("router.baml")
    assert _b.resolve() == _A.resolve()
    assert hashlib.sha256(_A.read_bytes()).hexdigest() == hashlib.sha256(_b.read_bytes()).hexdigest()


def test_classifier_baml_copies_byte_identical():
    ca = paths.DMAC_ASSISTANT_DIR / "baml_src" / "classifier.baml"
    cb = image_baml_source("classifier.baml")
    assert cb.resolve() == ca.resolve()
    assert ca.read_bytes() == cb.read_bytes()


def test_effective_enum_equals_every_declared_corpus_family_in_both_directions():
    snapshot = corpus_snapshot()
    assert declared_family_members(type_builder(snapshot)) == declared_labels(snapshot)
    assert len(declared_labels(snapshot)) > 0


def test_no_module_in_this_seam_reads_the_routing_capabilities_file():
    for name in ("family_labels.py", "baml_introspect.py"):
        src = (paths.ROUTER_DIR / name).read_text()
        assert "route_capabilities" not in src


def test_classifier_schema_has_no_destination_or_model_fields():
    text = (paths.DMAC_ASSISTANT_DIR / "baml_src" / "classifier.baml").read_text()
    body = text.split("class ClassificationDecision")[1].split("function")[0]
    assert "route" not in body
    assert "model_class" not in body
