"""Disk-space preflight, and the interactive image review it opens when short.

Ordering. Rebuilds and installs are the only things on these boxes that consume
disk in 8 GB steps, and they are also the only things that notice too late: the
build fails partway, or worse, succeeds onto a filesystem with nothing left for
MySQL. So the measurement is the first thing either command does, it always
prints, and above the floor it costs one line and no prompts.

Below the floor this opens a review. Two rules govern the whole module:

1. NOTHING IS EVER DELETED WITHOUT AN ANSWER. There is no flag that turns this
   into an automatic prune, and there is no `docker image prune -a`, no
   `docker system prune`, and nothing that accepts `--volumes` anywhere in this
   file. Every deletion is `docker image rm` against an explicit list the
   operator has just read. Volumes hold the seeded data (seek-filestore,
   seek-mysql-db, seek-solr-data, seek-cache, neo4j-data); losing one means a
   re-seed, so no code path here can reach them.

2. THE BUCKETER IS DEFAULT-DENY. An image is offered only when it matches a
   pattern recognised as safe to lose. Anything unrecognised is protected and
   reported as such. ``ci_profile`` moves the pre-filled ANSWER, never the
   protected set -- see test_the_protected_set_is_identical_on_every_profile.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from startup.lib import ui
from startup.lib.rebuild_policy import component_policies

#: Free space, in GB, below which a rebuild opens the review instead of
#: proceeding. Production is higher because the failure it prevents is worse:
#: a box that fills up mid-deploy takes the database down with it.
FLOORS_GB = {"local": 20, "dev": 20, "prod": 30}

#: An absent or unrecognised profile gets the most cautious floor, never the
#: least -- the same fail-closed rule startup applies to ci_profile everywhere
#: (startup/cli.py DEFAULT_CI_PROFILE, startup/steps/doctor.py).
DEFAULT_FLOOR_GB = 30

#: Tag prefixes that are never offered on any profile, whatever the answer.
#: baseline-20260805 is the frozen pre-merge production baseline; it is the
#: rollback of last resort and predates the GHCR pushes, so it may exist here
#: and nowhere else.
FROZEN_TAG_PREFIXES = ("baseline-20260805",)

_ROLLBACK_TAG = re.compile(r"^pre-\d{8}T\d{6}-")
_BASELINE_TAG = re.compile(r"^baseline-\d{8}-")
_SIZE = re.compile(r"^([0-9.]+)\s*([kKMGT]?B)$")
_UNITS = {"B": 1, "kB": 1000, "MB": 1000 ** 2, "GB": 1000 ** 3, "TB": 1000 ** 4}


@dataclass(frozen=True)
class DiskUsage:
    path: str
    total_bytes: int
    used_bytes: int
    free_bytes: int

    @property
    def free_gb(self) -> float:
        return self.free_bytes / 1000 ** 3

    @property
    def total_gb(self) -> float:
        return self.total_bytes / 1000 ** 3

    def __str__(self) -> str:
        return (
            f"{self.path}: {self.total_gb:.1f} GB total, {self.free_gb:.1f} GB free"
        )


@dataclass(frozen=True)
class LocalImage:
    image_id: str
    repository: str
    tag: str
    size_bytes: int
    created_since: str

    @property
    def ref(self) -> str:
        return f"{self.repository}:{self.tag}"

    @property
    def is_dangling(self) -> bool:
        return self.repository == "<none>" or self.tag == "<none>"


@dataclass(frozen=True)
class Bucket:
    key: str
    title: str
    images: tuple[LocalImage, ...]
    default_yes: bool
    detail: str = ""

    @property
    def nominal_bytes(self) -> int:
        """Sum of the SIZE column, which is an UPPER BOUND and not additive.

        Images share base layers, so deleting six 8.55 GB images does not free
        51 GB. Every rendering of this number has to say so, and the real figure
        comes from re-measuring free space afterwards.
        """
        return sum(i.size_bytes for i in self.images)


@dataclass
class Plan:
    buckets: tuple[Bucket, ...] = ()
    protected: dict[str, tuple[LocalImage, ...]] = field(default_factory=dict)


def floor_for(ci_profile: str | None) -> int:
    """GB of free space below which the review opens."""
    return FLOORS_GB.get((ci_profile or "").strip(), DEFAULT_FLOOR_GB)


def parse_size(text: str) -> int:
    """'8.55GB' -> bytes. Docker reports decimal units, not binary."""
    match = _SIZE.match(text.strip())
    if not match:
        return 0
    value, unit = match.groups()
    return int(float(value) * _UNITS.get(unit if unit != "kB" else "kB", 1))


def parse_images(text: str) -> list[LocalImage]:
    """Parse the tab-separated `docker images` format this module requests."""
    images: list[LocalImage] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        image_id, repository, tag, size, created = (p.strip() for p in parts[:5])
        images.append(
            LocalImage(
                image_id=image_id,
                repository=repository,
                tag=tag,
                size_bytes=parse_size(size),
                created_since=created,
            )
        )
    return images


def _first_party_refs(compose_project_name: str) -> tuple[set[str], set[str]]:
    """(the four current local refs, the repositories startup builds into)."""
    policies = component_policies(compose_project_name)["custom-stack"].images
    local = {image.local_image for image in policies}
    repos = {ref.rsplit(":", 1)[0] for ref in local}
    repos |= {image.registry_image for image in policies}
    return local, repos


def _is_frozen(image: LocalImage) -> bool:
    return any(image.tag.startswith(prefix) for prefix in FROZEN_TAG_PREFIXES)


def build_plan(
    images: list[LocalImage],
    container_image_refs: set[str],
    compose_project_name: str,
    ci_profile: str | None,
) -> Plan:
    """Sort every local image into "may be offered" or "protected, and why"."""
    current_refs, owned_repos = _first_party_refs(compose_project_name)

    # A container pins an image ID, not a name, so protection has to follow the
    # ID: otherwise a sibling tag of a running image looks deletable.
    in_use_ids = {
        i.image_id for i in images
        if i.ref in container_image_refs or i.image_id in container_image_refs
    }
    in_use_ids |= {
        ref for ref in container_image_refs if any(ref == i.image_id for i in images)
    }

    # The newest rollback tag per repository IS the rollback point. Tags sort
    # lexically by their embedded pre-YYYYMMDDTHHMMSS stamp, so no clock or
    # docker CreatedSince string is involved.
    newest_rollback: dict[str, str] = {}
    for image in images:
        if _ROLLBACK_TAG.match(image.tag):
            best = newest_rollback.get(image.repository)
            if best is None or image.tag > best:
                newest_rollback[image.repository] = image.tag

    protected: dict[str, list[LocalImage]] = {}
    old_rollback: list[LocalImage] = []
    registry_baselines: list[LocalImage] = []

    def protect(reason: str, image: LocalImage) -> None:
        protected.setdefault(reason, []).append(image)

    for image in images:
        if image.is_dangling:
            # No name to delete; `docker image prune -f` is their bucket.
            protect("dangling (offered as a prune, not by name)", image)
        elif image.image_id in in_use_ids:
            protect("in use by a container", image)
        elif _is_frozen(image):
            protect("frozen baseline, never deleted", image)
        elif image.ref in current_refs:
            protect("first-party image the stack runs on", image)
        elif image.repository not in owned_repos:
            protect("third-party image startup does not build", image)
        elif newest_rollback.get(image.repository) == image.tag:
            protect("the rollback point for its component", image)
        elif _ROLLBACK_TAG.match(image.tag):
            old_rollback.append(image)
        elif _BASELINE_TAG.match(image.tag):
            registry_baselines.append(image)
        else:
            # Default deny. Something put this tag here on purpose.
            protect("unrecognised tag, left alone", image)

    aggressive = (ci_profile or "").strip() in {"local", "dev", "prod"}
    buckets: list[Bucket] = []
    if old_rollback:
        buckets.append(Bucket(
            key="old_rollback",
            title=f"{len(old_rollback)} rollback tags older than the current rollback point",
            images=tuple(sorted(old_rollback, key=lambda i: i.ref)),
            default_yes=aggressive,
            detail="the newest pre-* per component is kept; these are the ones behind it",
        ))
    if registry_baselines:
        buckets.append(Bucket(
            key="registry_baseline",
            title=f"{len(registry_baselines)} local registry baseline tags",
            images=tuple(sorted(registry_baselines, key=lambda i: i.ref)),
            default_yes=aggressive,
            detail="these were pushed to GHCR, which is where the off-box rollback lives",
        ))
    return Plan(buckets=tuple(buckets), protected={k: tuple(v) for k, v in protected.items()})


# ---------------------------------------------------------------------------
# Everything below shells out. Read-only unless a caller passes an answer.
# ---------------------------------------------------------------------------

def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True)


def docker_root() -> str:
    """The filesystem docker actually writes to, not necessarily /."""
    result = _run(["docker", "info", "--format", "{{.DockerRootDir}}"])
    root = result.stdout.strip() if result.returncode == 0 else ""
    if root and Path(root).exists():
        return root
    # Same fallback ladder prereqs.run_all already uses.
    return "/var/lib/docker" if Path("/var/lib/docker").exists() else "/"


def measure(path: str) -> DiskUsage:
    total, used, free = shutil.disk_usage(path)
    return DiskUsage(path=path, total_bytes=total, used_bytes=used, free_bytes=free)


def list_images() -> list[LocalImage]:
    result = _run([
        "docker", "images", "--format",
        "{{.ID}}\t{{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}",
    ])
    return parse_images(result.stdout) if result.returncode == 0 else []


def container_image_refs() -> set[str]:
    """Every image named by a container, running or not."""
    result = _run(["docker", "ps", "-a", "--format", "{{.Image}}"])
    if result.returncode != 0:
        # Unknown means protect everything, not offer everything.
        raise RuntimeError(f"cannot read containers: {result.stderr.strip()}")
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def system_df() -> str:
    result = _run(["docker", "system", "df"])
    return result.stdout if result.returncode == 0 else ""


def build_cache_total_bytes() -> int:
    """What `docker builder prune -af` would free: the whole cache, not the
    'RECLAIMABLE' column, which is only the part no image still references."""
    result = _run(["docker", "system", "df", "--format", "{{.Type}}\t{{.Size}}"])
    if result.returncode != 0:
        return 0
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 2 and parts[0].strip() == "Build Cache":
            return parse_size(parts[1])
    return 0


def remove_images(refs: list[str]) -> list[tuple[str, bool, str]]:
    """`docker image rm` each ref, one at a time so one failure is not fatal."""
    results = []
    for ref in refs:
        result = _run(["docker", "image", "rm", ref])
        results.append((ref, result.returncode == 0, result.stderr.strip()))
    return results


def prune_dangling() -> tuple[bool, str]:
    """`docker image prune -f`: untagged, unreferenced layers only. Never -a."""
    result = _run(["docker", "image", "prune", "-f"])
    return result.returncode == 0, (result.stdout or result.stderr).strip()


def prune_build_cache() -> tuple[bool, str]:
    result = _run(["docker", "builder", "prune", "-af"])
    return result.returncode == 0, (result.stdout or result.stderr).strip()


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

@dataclass
class PreflightResult:
    proceed: bool
    floor_gb: int
    usage_before: DiskUsage
    usage_after: DiskUsage | None = None
    reason: str = ""

    @property
    def freed_gb(self) -> float:
        if self.usage_after is None:
            return 0.0
        return (self.usage_after.free_bytes - self.usage_before.free_bytes) / 1000 ** 3


def _default_confirm(question: str, default: bool = False) -> bool:
    import typer

    return typer.confirm(question, default=default)


def _gb(byte_count: int) -> str:
    return f"{byte_count / 1000 ** 3:.1f} GB"


def _report_protected(plan: Plan) -> None:
    if not plan.protected:
        return
    ui.info("protected, not offered:")
    for reason, images in sorted(plan.protected.items()):
        ui.info(f"    {len(images):>3}  {reason}")


def run_preflight(
    *,
    ci_profile: str | None,
    compose_project_name: str,
    skip: bool = False,
    floor_override: int | None = None,
    interactive: bool = True,
    confirm=None,
) -> PreflightResult:
    """Measure first, always print, and open the review only when short."""
    confirm = confirm or _default_confirm
    floor = floor_override if floor_override is not None else floor_for(ci_profile)
    shown_profile = (ci_profile or "").strip() or "absent -> prod"

    before = measure(docker_root())
    ui.info(f"Disk {before}")
    ui.info(f"Floor for profile '{shown_profile}': {floor} GB")

    if skip:
        ui.warn("purge review skipped by --no-disk-check; the measurement above still stands")
        return PreflightResult(True, floor, before, reason="skipped")

    if before.free_gb >= floor:
        ui.ok(f"{before.free_gb:.1f} GB free, at or above the {floor} GB floor")
        return PreflightResult(True, floor, before, reason="above floor")

    ui.banner(f"Disk below the {floor} GB floor — image review")
    ui.warn(
        f"{before.free_gb:.1f} GB free. Nothing below is deleted without an answer, "
        "and no volume is reachable from here at all."
    )
    df = system_df()
    if df:
        for line in df.splitlines():
            ui.info(f"    {line}")

    try:
        in_use = container_image_refs()
    except RuntimeError as exc:
        # Not knowing what is in use is the one state where offering nothing is
        # the only safe answer. It must never degrade to "assume nothing is".
        ui.fail(str(exc))
        ui.remediation(
            "the review cannot prove any image is unused while docker will not "
            "list containers; fix docker, or rebuild with --no-disk-check"
        )
        return PreflightResult(False, floor, before, reason="container list unreadable")

    plan = build_plan(list_images(), in_use, compose_project_name, ci_profile)
    _report_protected(plan)

    dangling = [i for i in plan.protected.get("dangling (offered as a prune, not by name)", ())]
    cache_bytes = build_cache_total_bytes()

    if not interactive:
        # A hooked rebuild has no terminal. Print the plan and stop, rather than
        # blocking forever on a question nobody can answer.
        ui.warn("not a terminal, so nothing is being asked or deleted. Candidates:")
        for bucket in plan.buckets:
            ui.info(f"    {bucket.title} (up to {_gb(bucket.nominal_bytes)} nominal)")
            for image in bucket.images:
                ui.info(f"        docker image rm {image.ref}")
        if dangling:
            ui.info(f"    {len(dangling)} dangling layers: docker image prune -f")
        if cache_bytes:
            ui.info(f"    build cache {_gb(cache_bytes)}: docker builder prune -af")
        return PreflightResult(False, floor, before, reason="non-interactive")

    for bucket in plan.buckets:
        ui.info("")
        ui.warn(f"{bucket.title} — up to {_gb(bucket.nominal_bytes)}")
        ui.info(f"    {bucket.detail}")
        ui.info("    layers are shared, so the real figure is lower than that")
        for image in bucket.images:
            ui.info(f"      {image.ref}  ({image.created_since})")
        if confirm(f"Delete the {bucket.title}?", bucket.default_yes):
            for ref, ok, detail in remove_images([i.ref for i in bucket.images]):
                (ui.ok if ok else ui.warn)(f"    {ref}: {'removed' if ok else detail}")

    if dangling:
        ui.info("")
        if confirm(
            f"Prune {len(dangling)} dangling layers (untagged and unreferenced)?", True
        ):
            ok, detail = prune_dangling()
            (ui.ok if ok else ui.warn)(f"    {detail.splitlines()[-1] if detail else 'pruned'}")

    # Last on purpose: pruning the build cache first leaves layers pinned by
    # images the operator is about to delete anyway.
    if cache_bytes:
        ui.info("")
        if confirm(
            f"Purge the entire build cache ({_gb(cache_bytes)})? "
            "Nothing breaks; the next build is cold and therefore slow.",
            True,
        ):
            ok, detail = prune_build_cache()
            (ui.ok if ok else ui.warn)(f"    {detail.splitlines()[-1] if detail else 'pruned'}")

    after = measure(before.path)
    result = PreflightResult(True, floor, before, usage_after=after)
    ui.info("")
    ui.ok(f"freed {result.freed_gb:.1f} GB — now {after.free_gb:.1f} GB free")

    if after.free_gb < floor:
        short = floor - after.free_gb
        result.proceed = confirm(
            f"Still {short:.1f} GB short of the {floor} GB floor. "
            "Proceed with the rebuild anyway?",
            False,
        )
        result.reason = "still short" if not result.proceed else "proceeding while short"
    return result
