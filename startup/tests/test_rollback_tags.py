"""Fail-fast local rollback tagging for every first-party rebuild."""
import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from startup.steps.rollback_tags import RollbackTagError, create_verified


NOW = datetime.datetime(2026, 8, 14, 12, 34, 56)


@patch("startup.lib.docker_ops.subprocess.run")
@patch("startup.steps.rollback_tags.subprocess.run")
def test_create_verified_tags_before_build_with_matching_identity(
    mock_run: MagicMock, mock_docker: MagicMock,
) -> None:
    def dispatch(args, **kwargs):
        if args[:4] == ["git", "-C", "/repo", "rev-parse"]:
            return MagicMock(returncode=0, stdout="abc1234\n", stderr="")
        if args[:4] == ["docker", "image", "ls", "-q"]:
            return MagicMock(returncode=0, stdout="feedface\n", stderr="")
        if args[:3] == ["docker", "image", "inspect"]:
            return MagicMock(returncode=0, stdout="sha256:feedface\n", stderr="")
        if args[:2] == ["docker", "tag"]:
            return MagicMock(returncode=0, stdout="", stderr="")
        raise AssertionError(args)

    mock_run.side_effect = dispatch
    mock_docker.side_effect = dispatch
    tags = create_verified(
        ["nextseek-nextseek:latest", "dmac-assistant:poc"],
        Path("/repo"),
        now=NOW,
    )
    assert [tag.tag for tag in tags] == [
        "nextseek-nextseek:pre-20260814T123456-abc1234",
        "dmac-assistant:pre-20260814T123456-abc1234",
    ]
    assert all(tag.image_id == "sha256:feedface" for tag in tags)


@patch("startup.lib.docker_ops.subprocess.run")
@patch("startup.steps.rollback_tags.subprocess.run")
def test_absent_source_is_a_first_build_not_an_error(
    mock_run: MagicMock, mock_docker: MagicMock,
) -> None:
    """An image that does not exist yet cannot be built over, so there is
    nothing for a rollback point to protect. Recovering a pruned image is
    exactly when a hard refusal costs the most, so this degrades instead."""
    def dispatch(args, **kwargs):
        if args[0] == "git":
            return MagicMock(returncode=0, stdout="abc1234\n", stderr="")
        if args[:4] == ["docker", "image", "ls", "-q"]:
            return MagicMock(returncode=0, stdout="", stderr="")
        raise AssertionError(f"absent image must not be inspected or tagged: {args}")

    mock_run.side_effect = dispatch
    mock_docker.side_effect = dispatch

    assert create_verified(["dmac-assistant:poc"], Path("/repo"), now=NOW) == ()

    every_call = mock_run.call_args_list + mock_docker.call_args_list
    assert not any(call.args[0][:2] == ["docker", "tag"] for call in every_call)


@patch("startup.lib.docker_ops.subprocess.run")
@patch("startup.steps.rollback_tags.subprocess.run")
def test_unreachable_daemon_still_fails_before_any_tag(
    mock_run: MagicMock, mock_docker: MagicMock,
) -> None:
    """The other half of the contract: a daemon that cannot answer is an
    outage, never a first build. `docker image inspect` exits 1 for both, so
    presence is probed with `docker image ls -q`, which exits 0 with empty
    stdout for an absent image and non-zero only when docker itself fails."""
    def dispatch(args, **kwargs):
        if args[0] == "git":
            return MagicMock(returncode=0, stdout="abc1234\n", stderr="")
        return MagicMock(
            returncode=1,
            stdout="",
            stderr="Cannot connect to the Docker daemon at unix:///var/run/docker.sock.",
        )

    mock_run.side_effect = dispatch
    mock_docker.side_effect = dispatch

    with pytest.raises(RollbackTagError, match="Cannot connect to the Docker daemon"):
        create_verified(["nextseek-nextseek:latest"], Path("/repo"), now=NOW)

    every_call = mock_run.call_args_list + mock_docker.call_args_list
    assert not any(call.args[0][:2] == ["docker", "tag"] for call in every_call)


@patch("startup.lib.docker_ops.subprocess.run")
@patch("startup.steps.rollback_tags.subprocess.run")
def test_mixed_presence_tags_only_the_image_that_exists(
    mock_run: MagicMock, mock_docker: MagicMock,
) -> None:
    """`--component custom-stack` spans four images. One of them missing must
    not cost the other three their rollback points."""
    def dispatch(args, **kwargs):
        if args[0] == "git":
            return MagicMock(returncode=0, stdout="abc1234\n", stderr="")
        if args[:4] == ["docker", "image", "ls", "-q"]:
            present = args[4] == "nextseek-nextseek:latest"
            return MagicMock(
                returncode=0, stdout="feedface\n" if present else "", stderr=""
            )
        if args[:3] == ["docker", "image", "inspect"]:
            return MagicMock(returncode=0, stdout="sha256:feedface\n", stderr="")
        if args[:2] == ["docker", "tag"]:
            return MagicMock(returncode=0, stdout="", stderr="")
        raise AssertionError(args)

    mock_run.side_effect = dispatch
    mock_docker.side_effect = dispatch

    tags = create_verified(
        ["nextseek-nextseek:latest", "dmac-assistant:poc"], Path("/repo"), now=NOW
    )

    assert [tag.source for tag in tags] == ["nextseek-nextseek:latest"]
    assert [tag.tag for tag in tags] == ["nextseek-nextseek:pre-20260814T123456-abc1234"]


@patch("startup.lib.docker_ops.subprocess.run")
@patch("startup.steps.rollback_tags.subprocess.run")
def test_identity_mismatch_fails_closed(
    mock_run: MagicMock, mock_docker: MagicMock,
) -> None:
    inspect_ids = iter(["sha256:old\n", "sha256:wrong\n"])

    def dispatch(args, **kwargs):
        if args[0] == "git":
            return MagicMock(returncode=0, stdout="abc1234\n", stderr="")
        if args[:4] == ["docker", "image", "ls", "-q"]:
            return MagicMock(returncode=0, stdout="feedface\n", stderr="")
        if args[:3] == ["docker", "image", "inspect"]:
            return MagicMock(returncode=0, stdout=next(inspect_ids), stderr="")
        return MagicMock(returncode=0, stdout="", stderr="")

    mock_run.side_effect = dispatch
    mock_docker.side_effect = dispatch
    with pytest.raises(RollbackTagError, match="identity mismatch"):
        create_verified(["nextseek-nextseek:latest"], Path("/repo"), now=NOW)
