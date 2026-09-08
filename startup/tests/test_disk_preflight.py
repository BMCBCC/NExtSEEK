"""Disk preflight: measure, and only then propose what may be deleted.

The bucketer is default-deny. An image is offered for deletion only when it
matches a pattern this module recognises as safe to lose; anything it does not
understand is protected. Every test below is about what must NOT be offered.
"""
from __future__ import annotations

import pytest

from startup.steps import disk_preflight as dp


# ---------------------------------------------------------------------------
# Floors, from .instance.json's ci_profile
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "profile,expected",
    [("local", 20), ("dev", 20), ("prod", 30)],
)
def test_floor_per_profile(profile: str, expected: int) -> None:
    assert dp.floor_for(profile) == expected


@pytest.mark.parametrize("profile", ["", None, "staging", "PROD"])
def test_an_absent_or_unknown_profile_gets_the_production_floor(profile) -> None:
    """The rule startup already applies to ci_profile everywhere: a box nobody
    configured gets the most cautious value, never the least."""
    assert dp.floor_for(profile) == 30


# ---------------------------------------------------------------------------
# Parsing docker's output
# ---------------------------------------------------------------------------

IMAGE_LINES = "\n".join([
    "e7129d8dcef9\tnextseek-nextseek\tlatest\t8.55GB\t3 days ago",
    "746306f96d3e\tnextseek-nextseek\tpre-20260903T183059-4bf5d6a2\t8.55GB\t3 days ago",
    "17c1b9911613\tnextseek-nextseek\tpre-20260903T180726-4bf5d6a2\t8.55GB\t3 days ago",
    "21ffc4dbaefc\tnextseek-nextseek\tpre-20260902T115229-9ee81f09\t8.55GB\t5 days ago",
    "aaaaaaaaaaaa\tdmac-assistant\tpoc\t2.64GB\t2 hours ago",
    "bbbbbbbbbbbb\tnextseek-ns-sidecar\tlatest\t306MB\t3 weeks ago",
    "cccccccccccc\tnextseek-bedrock-proxy\tlatest\t369MB\t3 weeks ago",
    "dddddddddddd\tghcr.io/biomicrocenter/nextseek\tbaseline-20260907-abc1234\t8.55GB\t1 day ago",
    "eeeeeeeeeeee\tghcr.io/biomicrocenter/nextseek\tbaseline-20260805-99999999\t8.40GB\t1 month ago",
    "ffffffffffff\tmysql\t8.0\t1.1GB\t4 months ago",
    "999999999999\t<none>\t<none>\t1.2GB\t2 days ago",
])


def test_parse_images_reads_every_field() -> None:
    images = dp.parse_images(IMAGE_LINES)
    assert len(images) == 11
    first = images[0]
    assert first.image_id == "e7129d8dcef9"
    assert first.repository == "nextseek-nextseek"
    assert first.tag == "latest"
    assert first.ref == "nextseek-nextseek:latest"
    assert first.size_bytes == pytest.approx(8.55 * 1000 ** 3, rel=0.01)


def test_parse_images_marks_a_dangling_layer() -> None:
    dangling = [i for i in dp.parse_images(IMAGE_LINES) if i.is_dangling]
    assert [i.image_id for i in dangling] == ["999999999999"]


@pytest.mark.parametrize(
    "text,expected_gb",
    [("8.55GB", 8.55), ("369MB", 0.369), ("1.1GB", 1.1), ("512kB", 0.000512), ("0B", 0.0)],
)
def test_size_parsing(text: str, expected_gb: float) -> None:
    assert dp.parse_size(text) == pytest.approx(expected_gb * 1000 ** 3, rel=0.01)


# ---------------------------------------------------------------------------
# Bucketing: what may be offered, and far more importantly what may not
# ---------------------------------------------------------------------------

def _plan(in_use_refs=(), profile="dev"):
    return dp.build_plan(
        images=dp.parse_images(IMAGE_LINES),
        container_image_refs=set(in_use_refs),
        compose_project_name="nextseek",
        ci_profile=profile,
    )


def _offered(plan) -> set[str]:
    return {img.ref for bucket in plan.buckets for img in bucket.images}


def _protected_reason(plan, ref: str) -> str | None:
    for reason, images in plan.protected.items():
        if any(i.ref == ref for i in images):
            return reason
    return None


def test_the_newest_rollback_tag_per_repository_is_kept() -> None:
    plan = _plan()
    newest = "nextseek-nextseek:pre-20260903T183059-4bf5d6a2"
    assert newest not in _offered(plan)
    assert "rollback point" in _protected_reason(plan, newest)


def test_older_rollback_tags_are_offered() -> None:
    plan = _plan()
    offered = _offered(plan)
    assert "nextseek-nextseek:pre-20260903T180726-4bf5d6a2" in offered
    assert "nextseek-nextseek:pre-20260902T115229-9ee81f09" in offered


def test_a_first_party_latest_is_never_offered() -> None:
    plan = _plan()
    offered = _offered(plan)
    for ref in (
        "nextseek-nextseek:latest",
        "dmac-assistant:poc",
        "nextseek-ns-sidecar:latest",
        "nextseek-bedrock-proxy:latest",
    ):
        assert ref not in offered, f"{ref} would break the rebuild's own image check"


def test_the_frozen_baseline_is_never_offered() -> None:
    plan = _plan()
    assert "ghcr.io/biomicrocenter/nextseek:baseline-20260805-99999999" not in _offered(plan)


def test_other_registry_baselines_are_offered() -> None:
    plan = _plan()
    assert "ghcr.io/biomicrocenter/nextseek:baseline-20260907-abc1234" in _offered(plan)


def test_third_party_images_are_never_offered() -> None:
    plan = _plan()
    assert "mysql:8.0" not in _offered(plan)
    assert "third-party" in _protected_reason(plan, "mysql:8.0")


def test_an_image_a_container_uses_is_never_offered() -> None:
    """Even when it is otherwise a deletable old rollback tag."""
    old = "nextseek-nextseek:pre-20260902T115229-9ee81f09"
    plan = _plan(in_use_refs=[old])
    assert old not in _offered(plan)
    assert "in use" in _protected_reason(plan, old)


def test_every_tag_of_an_in_use_image_is_protected_by_its_id() -> None:
    """A container pins an image ID, not a name. Protection has to follow the
    ID or a sibling tag of a running image becomes deletable."""
    lines = IMAGE_LINES + "\n17c1b9911613\tnextseek-nextseek\tpre-20260901T000000-deadbeef\t8.55GB\t8 days ago"
    plan = dp.build_plan(
        images=dp.parse_images(lines),
        container_image_refs={"nextseek-nextseek:pre-20260903T180726-4bf5d6a2"},
        compose_project_name="nextseek",
        ci_profile="dev",
    )
    offered = {img.ref for b in plan.buckets for img in b.images}
    assert "nextseek-nextseek:pre-20260901T000000-deadbeef" not in offered


def test_an_unrecognised_tag_is_protected_rather_than_offered() -> None:
    """Default deny: the bucketer offers only what it positively recognises."""
    lines = IMAGE_LINES + "\n111111111111\tnextseek-nextseek\tsomeones-experiment\t8.55GB\t1 day ago"
    plan = dp.build_plan(
        images=dp.parse_images(lines),
        container_image_refs=set(),
        compose_project_name="nextseek",
        ci_profile="dev",
    )
    ref = "nextseek-nextseek:someones-experiment"
    assert ref not in {i.ref for b in plan.buckets for i in b.images}
    assert _protected_reason(plan, ref) is not None


def test_dangling_layers_are_not_offered_by_reference() -> None:
    """They have no name to delete; `docker image prune -f` is their bucket."""
    plan = _plan()
    assert not any(img.is_dangling for b in plan.buckets for img in b.images)


def test_a_namespaced_instance_protects_its_own_app_image() -> None:
    lines = "\n".join([
        "aaa111\tnextseek-v2-nextseek\tlatest\t8.55GB\t1 day ago",
        "bbb222\tnextseek-v2-nextseek\tpre-20260903T100000-aaaaaaa\t8.55GB\t2 days ago",
        "ccc333\tnextseek-v2-nextseek\tpre-20260902T100000-bbbbbbb\t8.55GB\t3 days ago",
    ])
    plan = dp.build_plan(
        images=dp.parse_images(lines),
        container_image_refs=set(),
        compose_project_name="nextseek-v2",
        ci_profile="dev",
    )
    offered = {i.ref for b in plan.buckets for i in b.images}
    assert "nextseek-v2-nextseek:latest" not in offered
    assert "nextseek-v2-nextseek:pre-20260903T100000-aaaaaaa" not in offered  # rollback point
    assert "nextseek-v2-nextseek:pre-20260902T100000-bbbbbbb" in offered


# ---------------------------------------------------------------------------
# Per-profile defaults: the SUGGESTION changes, never what is protected
# ---------------------------------------------------------------------------

def test_the_protected_set_is_identical_on_every_profile() -> None:
    """Profile moves the pre-filled answer. It never widens what may be lost."""
    sets = {
        profile: {i.ref for b in _plan(profile=profile).buckets for i in b.images}
        for profile in ("local", "dev", "prod")
    }
    assert sets["local"] == sets["dev"] == sets["prod"]


# ---------------------------------------------------------------------------
# Orchestration: measure, then ask, then act. Never the other way round.
# ---------------------------------------------------------------------------

class _Recorder:
    """Stands in for every docker call the review makes."""

    def __init__(self, free_gb: float, after_gb: float | None = None):
        self.free_gb = free_gb
        self.after_gb = after_gb if after_gb is not None else free_gb
        self.measured = 0
        self.removed: list[str] = []
        self.pruned: list[str] = []
        self.asked: list[str] = []

    def measure(self, path: str) -> dp.DiskUsage:
        self.measured += 1
        gb = self.free_gb if self.measured == 1 else self.after_gb
        return dp.DiskUsage(
            path=path, total_bytes=200 * 1000 ** 3,
            used_bytes=int((200 - gb) * 1000 ** 3), free_bytes=int(gb * 1000 ** 3),
        )

    def install(self, monkeypatch, answers: dict[str, bool] | bool = True):
        monkeypatch.setattr(dp, "docker_root", lambda: "/var/lib/docker")
        monkeypatch.setattr(dp, "measure", self.measure)
        monkeypatch.setattr(dp, "system_df", lambda: "TYPE  SIZE  RECLAIMABLE\n")
        monkeypatch.setattr(dp, "list_images", lambda: dp.parse_images(IMAGE_LINES))
        monkeypatch.setattr(dp, "container_image_refs", lambda: set())
        monkeypatch.setattr(dp, "build_cache_total_bytes", lambda: 15 * 1000 ** 3)
        monkeypatch.setattr(
            dp, "remove_images",
            lambda refs: self.removed.extend(refs) or [(r, True, "") for r in refs],
        )
        monkeypatch.setattr(
            dp, "prune_dangling", lambda: (self.pruned.append("dangling"), (True, ""))[1]
        )
        monkeypatch.setattr(
            dp, "prune_build_cache", lambda: (self.pruned.append("cache"), (True, ""))[1]
        )

        def confirm(question: str, default: bool = False) -> bool:
            self.asked.append(question)
            if isinstance(answers, bool):
                return answers
            for key, value in answers.items():
                if key in question:
                    return value
            return False

        return confirm


def _preflight(rec, monkeypatch, answers=True, **kwargs):
    confirm = rec.install(monkeypatch, answers)
    return dp.run_preflight(
        ci_profile=kwargs.pop("ci_profile", "dev"),
        compose_project_name="nextseek",
        confirm=confirm,
        **kwargs,
    )


def test_above_the_floor_proceeds_without_asking_anything(monkeypatch) -> None:
    rec = _Recorder(free_gb=45.0)
    result = _preflight(rec, monkeypatch)
    assert result.proceed is True
    assert rec.asked == []
    assert rec.removed == [] and rec.pruned == []


def test_the_production_floor_is_what_opens_the_review_on_prod(monkeypatch) -> None:
    """25 GB free is fine on dev and not fine on prod."""
    dev = _Recorder(free_gb=25.0)
    assert _preflight(dev, monkeypatch, ci_profile="dev").proceed is True
    assert dev.asked == []

    prod = _Recorder(free_gb=25.0)
    _preflight(prod, monkeypatch, answers=False, ci_profile="prod")
    assert prod.asked != []


def test_answering_no_to_everything_deletes_nothing(monkeypatch) -> None:
    rec = _Recorder(free_gb=5.0)
    _preflight(rec, monkeypatch, answers=False)
    assert rec.removed == []
    assert rec.pruned == []
    assert rec.asked != []


def test_a_yes_removes_exactly_that_bucket_and_nothing_else(monkeypatch) -> None:
    rec = _Recorder(free_gb=5.0, after_gb=30.0)
    _preflight(rec, monkeypatch, answers={"rollback tags": True})
    assert rec.removed == [
        "nextseek-nextseek:pre-20260902T115229-9ee81f09",
        "nextseek-nextseek:pre-20260903T180726-4bf5d6a2",
    ]
    assert rec.pruned == []


def test_the_build_cache_is_offered_last(monkeypatch) -> None:
    """Images first: pruning the cache first leaves layers pinned by images the
    operator is about to delete anyway."""
    rec = _Recorder(free_gb=5.0, after_gb=30.0)
    _preflight(rec, monkeypatch, answers=True)
    assert rec.pruned == ["dangling", "cache"]
    assert "build cache" in rec.asked[-1]


def test_a_non_interactive_run_never_prompts_and_refuses_to_proceed(monkeypatch) -> None:
    """A hooked rebuild with no terminal must not hang on a question."""
    rec = _Recorder(free_gb=5.0)
    result = _preflight(rec, monkeypatch, interactive=False)
    assert result.proceed is False
    assert rec.asked == []
    assert rec.removed == [] and rec.pruned == []


def test_skip_bypasses_the_whole_thing(monkeypatch) -> None:
    rec = _Recorder(free_gb=1.0)
    result = _preflight(rec, monkeypatch, skip=True)
    assert result.proceed is True
    assert rec.asked == []


def test_a_floor_override_wins_over_the_profile(monkeypatch) -> None:
    rec = _Recorder(free_gb=25.0)
    result = _preflight(rec, monkeypatch, ci_profile="prod", floor_override=10)
    assert result.proceed is True
    assert rec.asked == []


def test_it_re_measures_and_reports_what_was_really_freed(monkeypatch) -> None:
    """The SIZE column is an upper bound. Only a second measurement is true."""
    rec = _Recorder(free_gb=5.0, after_gb=28.0)
    result = _preflight(rec, monkeypatch, answers=True)
    assert rec.measured == 2
    assert result.freed_gb == pytest.approx(23.0, rel=0.01)
    assert result.proceed is True


def test_still_short_after_purging_asks_rather_than_blocking(monkeypatch) -> None:
    rec = _Recorder(free_gb=5.0, after_gb=9.0)
    result = _preflight(rec, monkeypatch, answers=True)
    assert any("anyway" in q for q in rec.asked)
    assert result.proceed is True  # because the recorder answered yes


def test_an_unreadable_container_list_stops_rather_than_offering_everything(
    monkeypatch,
) -> None:
    """Not knowing what is in use is the one state where offering nothing is
    the only safe answer. It must never degrade to 'assume nothing is in use'."""
    rec = _Recorder(free_gb=5.0)
    confirm = rec.install(monkeypatch)

    def explode():
        raise RuntimeError("cannot read containers: daemon unreachable")

    monkeypatch.setattr(dp, "container_image_refs", explode)

    result = dp.run_preflight(
        ci_profile="dev", compose_project_name="nextseek", confirm=confirm
    )

    assert result.proceed is False
    assert rec.removed == [] and rec.pruned == []
    assert rec.asked == []


def test_the_module_contains_no_blanket_prune_and_cannot_touch_a_volume() -> None:
    """A source-level guard on the two rules in the module docstring. Any of
    these appearing later would be a silent widening of what a deploy can lose."""
    import inspect

    source = inspect.getsource(dp)
    for forbidden in ('"system", "prune"', '"prune", "-a"', '"--volumes"', '"volume"'):
        assert forbidden not in source, f"forbidden docker call in disk_preflight: {forbidden}"
