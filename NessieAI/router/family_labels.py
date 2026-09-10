"""Corpus-owned classifier label space for Plan 018 V4-6.

Single read seam for declared task families from the NessieAI.tests.nessie_tests corpus only.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from NessieAI import paths

__all__ = [
    "CorpusSnapshot",
    "corpus_snapshot",
    "declared_labels",
    "type_builder",
    "runtime_type_builder",
]

logger = logging.getLogger(__name__)

# The hand-owned harness corpus, NessieAI/tests/nessie_tests/corpus.json. The live
# router reads it too, and every caller swallows a failure here, so a missing
# file is logged at ERROR in corpus_snapshot().
_CORPUS_PATH = paths.NESSIE_CORPUS


@dataclass(frozen=True)
class CorpusSnapshot:
    corpus_path: str
    corpus_sha256: str
    taxonomy_version: str
    families: tuple[str, ...]
    descriptions: dict[str, str]


def _repo_root() -> Path:
    return paths.REPO_ROOT


def corpus_snapshot(path: Path | None = None) -> CorpusSnapshot:
    corpus_path = path or _CORPUS_PATH
    try:
        raw = corpus_path.read_bytes()
    except OSError as exc:
        # Every caller catches this (router classification at router.py and the
        # posterior leg), so without this line both switch off silently.
        logger.error(
            "task-family corpus unreadable at %s (%s): classification and "
            "posterior routing are off",
            corpus_path,
            exc,
        )
        raise
    payload = json.loads(raw.decode())
    families_obj = payload.get("families") or {}
    if not isinstance(families_obj, dict):
        raise ValueError("corpus families must be an object")
    names = tuple(sorted(str(k) for k in families_obj.keys()))
    descriptions = {
        str(k): str((v or {}).get("description") or "")
        for k, v in families_obj.items()
    }
    taxonomy = str(payload.get("taxonomy_version") or payload.get("version") or "nessie_corpus_v1")
    return CorpusSnapshot(
        corpus_path=str(corpus_path),
        corpus_sha256=hashlib.sha256(raw).hexdigest(),
        taxonomy_version=taxonomy,
        families=names,
        descriptions=descriptions,
    )


def declared_labels(snapshot: CorpusSnapshot | None = None) -> set[str]:
    snap = snapshot or corpus_snapshot()
    return set(snap.families)


def type_builder(snapshot: CorpusSnapshot | None = None) -> dict[str, Any]:
    """Return a serializable TypeBuilder recipe for BAML dynamic enum injection."""
    snap = snapshot or corpus_snapshot()
    return {
        "taxonomy_version": snap.taxonomy_version,
        "corpus_sha256": snap.corpus_sha256,
        "members": [
            {"name": name, "description": snap.descriptions.get(name, "")}
            for name in snap.families
        ],
    }


def runtime_type_builder(snapshot: CorpusSnapshot | None = None):
    """Build the generated BAML ``TypeBuilder`` for ``ClassifiedFamily``.

    The serializable recipe above remains the auditable/source-derived view;
    this function is the runtime bridge that must be supplied to BAML.
    """
    from dmac_assistant.router.baml_client.type_builder import TypeBuilder

    builder = TypeBuilder()
    for member in type_builder(snapshot).get("members", []):
        value = builder.ClassifiedFamily.add_value(member["name"])
        description = member.get("description")
        if description:
            value.description(description)
    return builder
