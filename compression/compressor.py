from __future__ import annotations
from typing import Iterable, Optional, Tuple
import difflib
from ..sources.base import Revision
from ..storage.compressed_store import CompressedArticle
from .partitioner import optimal_partition_indices
from WikECD.logger import get_logger
import logging

from .metrics import (
    space_cost_from_partitions,
    time_cost_from_partitions,
    orig_size_from_sizes,
)

logger = get_logger("WikECD.compressor", level=logging.DEBUG)


def _ndiff(from_text: str, to_text: str) -> list[str]:
    return list(difflib.ndiff(from_text.splitlines(keepends=True),
                              to_text.splitlines(keepends=True)))


def compress_article(title: str, revisions: Iterable[Revision], time_budget: Optional[int] = None, *, solver: str = "heuristic", strategy: str = "auto", eps: float = 0.1, max_states: int = 100_000,) -> CompressedArticle:
    revs = list(revisions)
    if not revs:
        return CompressedArticle(title=title, anchors=[], patches={}, meta={"title": title, "count": 0})

    texts = [r.text for r in revs]
    sizes = [len(t) for t in texts]

    # NEW: keep IDs and timestamps for retrieval queries
    revids = [int(r.revid) for r in revs]
    timestamps = [r.timestamp for r in revs]

    chosen_transitions, partitions = optimal_partition_indices(
        sizes, time_budget=time_budget, solver=solver, strategy=strategy, eps=eps, max_states=max_states
    )

    anchors: list[int] = [part[0] for part in partitions]
    patches: dict[tuple[int, int], list[str]] = {}

    for part in partitions:
        base = part[0]
        prev = texts[base]
        for idx in part[1:]:
            nd = _ndiff(prev, texts[idx])
            patches[(idx-1, idx)] = nd
            prev = texts[idx]

    article = CompressedArticle(
        title=title,
        anchors=anchors,
        patches=patches,
        meta={
            "title": title,
            "count": len(revs),
            "partitions": partitions,
            "revids": revids,  # <— NEW
            "timestamps": timestamps,  # <— NEW (ISO-like strings from API/XML)
        }
    )

    # --- robustly populate article.base_texts from the input revisions (revs) ---
    import logging
    from WikECD.logger import get_logger
    logger = get_logger("WikECD.compressor", level=logging.DEBUG)

    try:
        # Normalize anchors into a list of ints
        anchors_attr = getattr(article, "anchors", None) or (
            article.meta.get("anchors") if getattr(article, "meta", None) else None)
        anchors_list = []
        if anchors_attr is None:
            anchors_list = []
        elif isinstance(anchors_attr, dict):
            anchors_list = sorted(int(k) for k in anchors_attr.keys())
        elif isinstance(anchors_attr, (list, tuple)):
            # Flatten groups like [[0,1],[2]] -> [0,2] and ensure ints
            flat = []
            for el in anchors_attr:
                if isinstance(el, (list, tuple)) and el:
                    try:
                        flat.append(int(el[0]))
                    except Exception:
                        pass
                else:
                    try:
                        flat.append(int(el))
                    except Exception:
                        pass
            anchors_list = sorted(set(flat))
        else:
            try:
                anchors_list = sorted(int(x) for x in anchors_attr)
            except Exception:
                anchors_list = []

        # Get the revisions list that was passed to compress_article (we expect it in scope)
        cvs_revs = None
        if "revs" in locals():
            cvs_revs = locals().get("revs")
        else:
            # fallback candidate names
            for cand in ("revisions", "rev_list", "revision_list"):
                if cand in locals():
                    cvs_revs = locals()[cand]
                    break

        base_texts_map = {}
        if cvs_revs is not None and anchors_list:
            # helper to extract text from a revision object or raw string
            def _rev_text(r):
                if r is None:
                    return None
                if isinstance(r, str):
                    return r
                if isinstance(r, bytes):
                    try:
                        return r.decode("utf-8")
                    except Exception:
                        return None
                for attr in ("text", "content", "body", "wikitext"):
                    if hasattr(r, attr):
                        v = getattr(r, attr)
                        if isinstance(v, (str, bytes)):
                            return v.decode("utf-8") if isinstance(v, bytes) else v
                # last resort: try str(r)
                try:
                    s = str(r)
                    return s
                except Exception:
                    return None

            for a in anchors_list:
                try:
                    ai = int(a)
                except Exception:
                    continue
                if cvs_revs is None:
                    break
                if 0 <= ai < len(cvs_revs):
                    txt = _rev_text(cvs_revs[ai])
                    if txt:
                        base_texts_map[ai] = txt

        if base_texts_map:
            article.base_texts = base_texts_map
            if not getattr(article, "meta", None):
                article.meta = {}
            article.meta["base_texts"] = base_texts_map
            logger.debug("compress_article: populated article.base_texts keys=%r", sorted(base_texts_map.keys()))
        else:
            logger.debug("compress_article: no base_texts found to populate (anchors=%r, revs_len=%s)", anchors_list,
                         (len(cvs_revs) if cvs_revs is not None else None))

    except Exception as e:
        # don't break compression if something goes wrong; log the exception
        logger.warning("Could not populate article.base_texts (non-fatal): %s", e)
    # --- end population block --

    # after partitions/anchors computed and article/meta created:
    orig_size = sum(len(r.text) for r in revisions)
    article.meta.setdefault("orig_size", orig_size)
    article.meta.setdefault("solver", solver)
    article.meta.setdefault("strategy", strategy)
    article.meta.setdefault("time_budget", time_budget)

    # --- end population block --

    # === Metrics & knobs ===
    # We already have: texts, sizes, partitions, solver/strategy/time_budget
    parts = partitions  # just an alias

    # Primary metrics
    space_cost = space_cost_from_partitions(sizes, parts)
    time_cost = time_cost_from_partitions(sizes, parts)
    orig_size = orig_size_from_sizes(sizes)

    # Persist for analytics
    article.meta["orig_size"] = orig_size
    article.meta["space_cost"] = space_cost
    article.meta["time_cost"] = time_cost
    article.meta["sizes"] = sizes
    article.meta["solver"] = solver
    article.meta["strategy"] = strategy
    article.meta["time_budget"] = time_budget
    article.meta["page_id"] = getattr(revs[0], "page_id", None)

    # Optional: exact chain lengths (better histogram)
    try:
        article.meta["chain_lengths"] = [len(p) for p in parts]
    except Exception:
        pass

    return article

