from __future__ import annotations
from typing import List, Dict, Tuple, Iterable
import difflib
from ..storage.compressed_store import CompressedArticle
from typing import Any, List, Optional
import warnings


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


def reconstruct_range(article: Any, start: int, length: int, *, base_texts: Optional[dict] = None) -> List[str]:
    """
    Reconstruct revisions [start, start+length) from a compressed article object.

    This implementation:
      - delegates to article methods if present,
      - otherwise performs anchor+patch based reconstruction,
      - crucially: mixes use of anchor full-texts and patches:
          * if an index is an anchor (has base_text), use it directly
          * otherwise apply patch i->i+1
      - advances from the nearest anchor <= start and picks up anchors encountered en route
    """
    # quick input checks
    if length <= 0 or start < 0:
        return []

    # 0) Delegate if possible
    for name in ("reconstruct_range", "get_range", "retrieve_range", "get_revisions_range"):
        fn = getattr(article, name, None)
        if callable(fn):
            res = fn(start, length)
            return list(res) if res is not None else []

    # 0b) Per-index API
    for name in ("get_revision", "get", "reconstruct", "retrieve"):
        fn = getattr(article, name, None)
        if callable(fn):
            out = []
            for i in range(start, start + length):
                out.append(fn(i))
            if out:
                return out

    # 1) discover anchors
    anchors = None
    cand_anchor_attrs = ["anchors", "anchor_indices", "base_indices", "anchor_list"]
    for a in cand_anchor_attrs:
        if hasattr(article, a):
            anchors = getattr(article, a)
            break
    if anchors is None and getattr(article, "meta", None):
        for key in ("anchors", "anchor_indices", "bases"):
            if key in article.meta:
                anchors = article.meta[key]
                break

    # normalize anchors -> anchors_list
    anchors_list = None
    if anchors is None:
        anchors_list = None
    else:
        if isinstance(anchors, dict):
            anchors_list = sorted(int(k) for k in anchors.keys())
        elif isinstance(anchors, list):
            flat = []
            for el in anchors:
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
                anchors_list = sorted(int(x) for x in anchors)
            except Exception:
                anchors_list = None

    # 2) discover patches
    patches = None
    cand_patch_attrs = ["patches", "deltas", "diffs", "edits"]
    for p in cand_patch_attrs:
        if hasattr(article, p):
            patches = getattr(article, p)
            break
    if patches is None and getattr(article, "meta", None):
        for key in ("patches", "deltas", "diffs", "edits"):
            if key in article.meta:
                patches = article.meta[key]
                break

    # 3) discover base_texts
    if base_texts is None:
        if hasattr(article, "base_texts"):
            base_texts = getattr(article, "base_texts")
        elif getattr(article, "meta", None):
            for k in ("base_texts", "bases", "base_text", "anchor_texts", "full_texts", "fulltexts"):
                if k in article.meta:
                    base_texts = article.meta[k]
                    break
        else:
            base_texts = None

    # normalize base_texts if list-like and anchors_list provided
    if base_texts is not None and not isinstance(base_texts, dict):
        try:
            if anchors_list and isinstance(base_texts, (list, tuple)) and len(base_texts) == len(anchors_list):
                base_texts = {anchors_list[i]: base_texts[i] for i in range(len(anchors_list))}
        except Exception:
            pass

    if base_texts is None:
        msg = (
            "reconstruct_range: no anchor full-texts (base_texts) found for the given article.\n\n"
            "To allow retrieval, your compressed article must include at least one stored full-text anchor.\n"
            "Provide article.base_texts = {anchor_idx: full_text} or pass base_texts=... to this function."
        )
        raise AttributeError(msg)

    if not anchors_list:
        raise AttributeError("reconstruct_range: anchors could not be parsed; found anchors={!r}".format(anchors))

    # ---------------- helper functions ----------------
    def _get_patch_for_step(patches_obj, i):
        if patches_obj is None:
            return None
        if isinstance(patches_obj, dict):
            if i in patches_obj:
                return patches_obj[i]
            if (i, i + 1) in patches_obj:
                return patches_obj[(i, i + 1)]
            if str(i) in patches_obj:
                return patches_obj[str(i)]
            if str((i, i + 1)) in patches_obj:
                return patches_obj[str((i, i + 1))]
            try:
                # fallback: positional access
                keys = list(patches_obj.keys())
                if i < len(keys):
                    return patches_obj[keys[i]]
            except Exception:
                return None
        try:
            return patches_obj[i]
        except Exception:
            return None

    def _apply_patch_step(text: str, patch_obj):
        if not patch_obj:
            return text
        if callable(patch_obj):
            return patch_obj(text)
        # handle list-of-ops like ['- old', '+ new']
        if isinstance(patch_obj, (list, tuple)) and all(isinstance(x, str) for x in patch_obj):
            old = None
            new = None
            for op in patch_obj:
                if op.startswith("- "):
                    old = op[2:]
                elif op.startswith("+ "):
                    new = op[2:]
            if old is not None and new is not None:
                if text == old:
                    return new
                if old in text:
                    return text.replace(old, new, 1)
                return new
        # serialized diff-match-patch string
        if isinstance(patch_obj, str):
            try:
                from diff_match_patch import diff_match_patch
            except Exception as e:
                raise RuntimeError(
                    "reconstruct_range: patch looks like diff-match-patch text but package is not installed."
                ) from e
            dmp = diff_match_patch()
            patch_list = dmp.patch_fromText(patch_obj)
            new_text, results = dmp.patch_apply(patch_list, text)
            return new_text
        raise TypeError(f"reconstruct_range: unsupported patch format {type(patch_obj)}")

    def has_base_text(idx: int) -> bool:
        if base_texts is None:
            return False
        if isinstance(base_texts, dict):
            return idx in base_texts or str(idx) in base_texts
        try:
            pos = anchors_list.index(idx)
            return pos < len(base_texts)
        except Exception:
            return False

    def get_base_text(idx: int) -> Optional[str]:
        if base_texts is None:
            return None
        if isinstance(base_texts, dict):
            if idx in base_texts:
                return base_texts[idx]
            if str(idx) in base_texts:
                return base_texts[str(idx)]
            return None
        try:
            pos = anchors_list.index(idx)
            return base_texts[pos]
        except Exception:
            return None

    # ---------------- find anchor to start from ----------------
    anchor = None
    for a in reversed(anchors_list):
        if int(a) <= start:
            anchor = int(a)
            break
    if anchor is None:
        anchor = anchors_list[0]

    # seed text for anchor
    seed_text = get_base_text(anchor)
    if seed_text is None:
        raise KeyError(f"reconstruct_range: base_texts missing the chosen anchor {anchor}")

    # ---------------- advance from anchor to `start` mixing anchors & patches ----------------
    cur_text = seed_text
    cur_idx = anchor
    while cur_idx < start:
        next_idx = cur_idx + 1
        # if next index is itself a base anchor, use it directly
        if has_base_text(next_idx):
            cur_text = get_base_text(next_idx)
            cur_idx = next_idx
            continue
        # else apply patch cur_idx -> next_idx
        patch_obj = _get_patch_for_step(patches, cur_idx)
        cur_text = _apply_patch_step(cur_text, patch_obj)
        cur_idx = next_idx

    # ---------------- collect requested range ----------------
    results: List[str] = []
    # first item at 'start'
    if has_base_text(start):
        cur_text = get_base_text(start)
    else:
        cur_text = cur_text
    results.append(cur_text)

    for idx in range(start, start + length - 1):
        next_idx = idx + 1
        if has_base_text(next_idx):
            cur_text = get_base_text(next_idx)
            results.append(cur_text)
            continue
        patch_obj = _get_patch_for_step(patches, idx)
        cur_text = _apply_patch_step(cur_text, patch_obj)
        results.append(cur_text)

    return results
