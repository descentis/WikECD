from __future__ import annotations
from typing import List, Sequence

def sizes_from_texts(texts: Sequence[str]) -> List[int]:
    return [len(t) for t in texts]

def approx_diffs_from_sizes(sizes: Sequence[int]) -> List[int]:
    """Approximate ||dr_i|| ≈ 2 * |s_i - s_{i-1}| for i=1..n-1."""
    return [2 * abs(sizes[i] - sizes[i-1]) for i in range(1, len(sizes))]

def memory_saved_values(diffs: Sequence[int], sizes: Sequence[int]) -> List[int]:
    """
    mr_i = ||dr_i|| - ||r_{i-1}||  (i corresponds to transition i: i in [1..n-1])
    Return for indices 1..n-1 as a list aligned to transitions (length n-1).
    """
    return [diffs[i-1] - sizes[i-1] for i in range(1, len(sizes))]

def time_cost_weights(diffs: Sequence[int], sizes: Sequence[int]) -> List[int]:
    """
    For transition i (i in 1..n-1): cost ~= s_{i-1} + ||dr_i||
    """
    return [sizes[i-1] + diffs[i-1] for i in range(1, len(sizes))]
