from __future__ import annotations
from typing import List, Set, Tuple
from .diff_utils import approx_diffs_from_sizes, memory_saved_values, time_cost_weights
from .knapsack import knapsack

def optimal_partition_indices(sizes: List[int], time_budget: int | None = None) -> Tuple[Set[int], List[List[int]]]:
    """
    Returns:
      chosen_transitions: set of transition indices (1..n-1) CHOSEN for deltas (I_opt)
      partitions: list of lists of absolute revision indices forming contiguous blocks.
    Convention:
      - Revisions are indexed 0..n-1.
      - A transition i corresponds to edge (i-1 -> i). If transition i is chosen, r_i is delta-stored.
      - A revision r_k is an ANCHOR if transition k is NOT chosen (or k==0).
    """
    n = len(sizes)
    if n == 0:
        return set(), []
    if n == 1:
        return set(), [[0]]

    if time_budget is None:
        time_budget = n * n  # empirical default

    diffs   = approx_diffs_from_sizes(sizes)
    values  = memory_saved_values(diffs, sizes)   # length n-1, indexed for i=1..n-1 mapped to 0..n-2
    weights = time_cost_weights(diffs, sizes)

    chosen_rel = set(knapsack(values, weights, time_budget))        # 0..n-2
    chosen_transitions = {i+1 for i in chosen_rel}                  # map back to 1..n-1

    # Build partitions from anchors: r_0 is always an anchor (start)
    partitions: List[List[int]] = []
    cur: List[int] = [0]
    for i in range(1, n):
        if i in chosen_transitions:
            cur.append(i)  # delta inside partition
        else:
            partitions.append(cur)
            cur = [i]      # new anchor
    if cur:
        partitions.append(cur)

    return chosen_transitions, partitions
