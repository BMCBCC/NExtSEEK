"""Guard that runtime CC code does not revive the legacy flat-root provisioning."""
from NessieAI import paths


ROOT = paths.CC_DIR
SERVICE = paths.REPO_ROOT / "nextseek_api" / "services" / "cc_assistant.py"
# cc_sweep stayed in the Django shell at nextseek_api/cc_assistant/. The run-1c
# live probe went to NessieAI/history/ (frozen), so it is no longer runtime code.
RUNTIME_FILES = [
    ROOT / "cc_config.py",
    ROOT / "cc_engine.py",
    paths.REPO_ROOT / "nextseek_api" / "cc_assistant" / "cc_sweep.py",
    SERVICE,
    # Routing policy moved out of SERVICE in Phase B; it is still runtime code.
    paths.ROUTER_DIR / "policy.py",
]


def test_legacy_config_symbols_are_gone_from_runtime_code():
    blob = "\n".join(path.read_text() for path in RUNTIME_FILES)

    for dead in (
        "host_dropbox_root",
        "host_scratch_root",
        "host_output_root",
        "host_cc_state_root",
        "cc_state_mount",
        "projects_for",
        "_DEFAULT_USER_PROJECTS",
        "DMAC_CC_USER_PROJECTS",
        "DMAC_HOST_DROPBOX_ROOT",
        "DMAC_HOST_SCRATCH_ROOT",
        "DMAC_HOST_OUTPUT_ROOT",
        "DMAC_HOST_CC_STATE_ROOT",
        "DMAC_SCRATCH_MOUNT",
        "DMAC_OUTPUT_MOUNT",
        "DMAC_CC_STATE_MOUNT",
    ):
        assert dead not in blob, f"legacy symbol {dead!r} still appears in runtime code"


def test_legacy_projects_mount_constant_is_gone():
    assert "/data/projects" not in (ROOT / "cc_engine.py").read_text()
