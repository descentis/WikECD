from __future__ import annotations
from typing import List, Dict, Iterable, Optional
from datetime import datetime, timezone
from ..storage.compressed_store import CompressedArticle
from .retrieval import retrieve_range


def _parse_iso(ts: str) -> datetime:
    # Handles "YYYY-MM-DDTHH:MM:SSZ" or ISO with offset
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def _ensure_meta(article: CompressedArticle, key: str):
    if key not in article.meta:
        raise KeyError(f"CompressedArticle.meta lacks '{key}'. Recompress with a newer WikECD that stores this field.")


def retrieve_by_indices(article: CompressedArticle, base_texts: Dict[int, str], indices: List[int]) -> List[str]:
    """Retrieve arbitrary indices; returns texts in the same order as indices."""
    outputs: List[str] = []
    for idx in indices:
        outputs.extend(retrieve_range(article, base_texts, idx, 0))
    return outputs


def retrieve_by_revid(
    article: CompressedArticle,
    base_texts: Dict[int, str],
    revids: List[int],
    *,
    missing: str = "warn"  # "warn" | "ignore" | "error"
) -> List[str]:
    """
    Retrieve revisions by Wikipedia revision IDs.
    Requires article.meta['revids'] aligned to indices 0..n-1.
    """
    _ensure_meta(article, "revids")
    id_list: List[int] = [int(x) for x in article.meta["revids"]]
    index_of: Dict[int, int] = {rid: i for i, rid in enumerate(id_list)}

    results: List[str] = []
    for rid in revids:
        idx = index_of.get(int(rid))
        if idx is None:
            msg = f"revid {rid} not found in this compressed article"
            if missing == "error":
                raise KeyError(msg)
            elif missing == "warn":
                print("[WikECD] WARNING:", msg)
            continue
        results.extend(retrieve_range(article, base_texts, idx, 0))
    return results


def retrieve_by_time(
    article: CompressedArticle,
    base_texts: Dict[int, str],
    start: Optional[str] = None,
    end: Optional[str] = None,
    *,
    inclusive: bool = True
) -> List[str]:
    """
    Retrieve all revisions whose timestamps fall in [start, end] (inclusive by default).
    Timestamps must be present as article.meta['timestamps'] aligned to indices.
    start/end: ISO-8601 like 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SSZ'
    """
    _ensure_meta(article, "timestamps")
    ts_list: List[str] = article.meta["timestamps"]

    # Build list of indices that match range
    idxs: List[int] = []
    dt_start = _parse_iso(start + "T00:00:00Z") if (start and len(start) == 10) else (_parse_iso(start) if start else None)
    dt_end   = _parse_iso(end + "T23:59:59Z")   if (end and len(end) == 10)   else (_parse_iso(end) if end else None)

    for i, ts in enumerate(ts_list):
        dt = _parse_iso(ts)
        ok = True
        if dt_start:
            ok = ok and (dt >= dt_start if inclusive else dt > dt_start)
        if dt_end:
            ok = ok and (dt <= dt_end if inclusive else dt < dt_end)
        if ok:
            idxs.append(i)

    # Retrieve sequentially (already sorted by index/time)
    outputs: List[str] = []
    last_idx = None
    for idx in idxs:
        # Optionally coalesce adjacent indices into a single retrieve_range call.
        outputs.extend(retrieve_range(article, base_texts, idx, 0))
        last_idx = idx
    return outputs
