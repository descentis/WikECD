from __future__ import annotations
from typing import Iterable, Optional, Tuple
import difflib
from ..sources.base import Revision
from ..storage.compressed_store import CompressedArticle
from .partitioner import optimal_partition_indices

def _ndiff(from_text: str, to_text: str) -> list[str]:
    return list(difflib.ndiff(from_text.splitlines(keepends=True),
                              to_text.splitlines(keepends=True)))

def compress_article(title: str, revisions: Iterable[Revision], time_budget: Optional[int] = None) -> CompressedArticle:
    revs = list(revisions)
    if not revs:
        return CompressedArticle(title=title, anchors=[], patches={}, meta={"title": title, "count": 0})

    texts = [r.text for r in revs]
    sizes = [len(t) for t in texts]

    chosen_transitions, partitions = optimal_partition_indices(sizes, time_budget=time_budget)

    # Build storage: for each partition, store base (full text) and ndiff patches to next
    anchors: list[int] = [part[0] for part in partitions]
    patches: dict[tuple[int, int], list[str]] = {}

    for part in partitions:
        base = part[0]
        prev = texts[base]
        for idx in part[1:]:
            nd = _ndiff(prev, texts[idx])
            patches[(idx-1, idx)] = nd  # store patch from prev->idx
            prev = texts[idx]

    return CompressedArticle(
        title=title,
        anchors=anchors,
        patches=patches,
        meta={"title": title, "count": len(revs), "partitions": partitions}
    )
