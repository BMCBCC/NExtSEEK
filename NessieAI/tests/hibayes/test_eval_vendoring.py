import importlib

from NessieAI import paths

_HIBAYES = paths.NESSIE_ROOT / "hibayes"
_EVAL_DOCKERFILE = paths.NESSIE_DOCKER_DIR / "eval" / "Dockerfile"


def test_eval_package_is_importable():
    assert importlib.import_module("NessieAI.hibayes") is not None


def test_the_dangling_exporter_reference_is_now_satisfied():
    mod = importlib.import_module("NessieAI.hibayes.exporter")
    assert hasattr(mod, "FailureMode")


def test_no_module_imports_from_a_dmac_assistant_eval_checkout():
    # rglob over a missing directory yields nothing, so without these two
    # asserts the guard would pass vacuously once its root moved.
    assert _HIBAYES.is_dir(), f"HiBayes package not found at {_HIBAYES}"
    modules = sorted(_HIBAYES.rglob("*.py"))
    assert modules, f"no Python modules under {_HIBAYES}"
    offenders = []
    for p in modules:
        text = p.read_text()
        if "dmac_assistant.eval" in text or "from tools.hibayes" in text:
            offenders.append(str(p.relative_to(paths.REPO_ROOT)))
    assert offenders == [], f"external eval imports remain: {offenders}"


def test_eval_dockerfile_builds_from_this_repo_not_a_bind_mount():
    df = _EVAL_DOCKERFILE.read_text()
    assert "COPY NessieAI/hibayes" in df
    assert "/work/src" not in df, "still expects a bind-mounted external checkout"
