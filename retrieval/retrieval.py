from __future__ import annotations
from typing import List, Dict, Tuple, Iterable
import difflib
from ..storage.compressed_store import CompressedArticle

def _apply_ndiff(prev_text: str, ndiff_lines: List[str]) -> str:
    # difflib.restore(ndiff, 2) reconstructs the "to" sequence
    after_lines = list(difflib.restore(ndiff_lines, 2))
    return "".join(after_lines)

def _find_partition(partitions: List[List[int]], idx: int) -> List[int]:
    for part in partitions:
        if idx in part:
            return part
    raise ValueError(f"revision index {idx} not found in any partition")

def retrieve_range(
    article: CompressedArticle,
    base_texts: Dict[int, str],
    start: int,
    length: int
) -> List[str]:
    """
    Retrieve revisions [start, start+length] as raw texts.
    Requires:
      - base_texts: dict of {anchor_index: full_text} for all anchors in article.anchors
    """
    if length < 0:
        raise ValueError("length must be >= 0")

    end = start + length
    parts = article.partitions()
    part = _find_partition(parts, start)
    base = part[0]
    if base not in base_texts:
        raise KeyError(f"Missing base text for anchor {base}")

    # Step 1: reconstruct up to `start`
    cur_text = base_texts[base]
    idx_in_part = part.index(start)
    # walk from base->start
    for i in range(1, idx_in_part + 1):
        u, v = part[i-1], part[i]
        patch = article.patches.get((u, v))
        if patch is None:
            # v must be an anchor starting a new block (shouldn't happen inside same part)
            raise KeyError(f"Missing patch for transition {(u, v)}")
        cur_text = _apply_ndiff(cur_text, patch)

    results = [cur_text]

    # Step 2: continue to end within same partition or across partitions
    cur_idx = start
    while cur_idx < end:
        # try next in same partition
        next_idx = cur_idx + 1
        if next_idx in part:
            patch = article.patches.get((cur_idx, next_idx))
            if patch is None:
                raise KeyError(f"Missing patch for transition {(cur_idx, next_idx)}")
            cur_text = _apply_ndiff(cur_text, patch)
            results.append(cur_text)
            cur_idx = next_idx
        else:
            # move to next partition's base
            # find which partition contains next_idx
            if next_idx > max(max(p) for p in parts):
                break
            next_part = _find_partition(parts, next_idx)
            base = next_part[0]
            if base not in base_texts:
                raise KeyError(f"Missing base text for anchor {base}")
            cur_text = base_texts[base]
            # walk up inside next partition until we reach `next_idx`
            for i in range(1, next_part.index(next_idx) + 1):
                u, v = next_part[i-1], next_part[i]
                patch = article.patches.get((u, v))
                if patch is None:
                    raise KeyError(f"Missing patch for transition {(u, v)}")
                cur_text = _apply_ndiff(cur_text, patch)
            results.append(cur_text)
            cur_idx = next_idx
            part = next_part

    return results
