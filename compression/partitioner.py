from __future__ import annotations
from typing import List, Set, Tuple, Optional
from .diff_utils import approx_diffs_from_sizes, memory_saved_values, time_cost_weights
from .knapsack import knapsack
from .knapsack_heuristic import heuristic_knapsack


def optimal_partition_indices(
    sizes: List[int],
    time_budget: Optional[int] = None,
    solver: str = "heuristic",        # "exact" uses DP; "heuristic" uses fast approximations
    strategy: str = "auto",            # "auto" | "greedy" | "fptas" | "sparse"
    eps: float = 0.1,
    max_states: int = 100_000
) -> Tuple[Set[int], List[List[int]]]:
    """
    Returns:
      chosen_transitions: set of transition indices (1..n-1) selected as deltas
      partitions: list of lists of revision indices (0-based) forming blocks
    """
    n = len(sizes)
    if n == 0:
        return set(), []
    if n == 1:
        return set(), [[0]]

    if time_budget is None:
        time_budget = n * n  # empirical default

    diffs   = approx_diffs_from_sizes(sizes)
    values  = memory_saved_values(diffs, sizes)   # length n-1 (for transitions 1..n-1)
    weights = time_cost_weights(diffs, sizes)

    # filter out non-positive value items (no memory save)
    items = [(i, v, w) for i, (v, w) in enumerate(zip(values, weights)) if v > 0 and w > 0]
    if not items:
        return set(), [[i] for i in range(n)]  # all anchors (no beneficial deltas)

    idxs, vals, wgts = zip(*items)  # idxs refer to 0..n-2 (transition i+1)
    if solver == "exact":
        chosen_rel = set(knapsack(list(vals), list(wgts), time_budget))
    else:
        chosen_rel = set(heuristic_knapsack(list(vals), list(wgts), time_budget, strategy=strategy, eps=eps, max_states=max_states))

    # map back to transitions 1..n-1
    chosen_transitions = { (idxs[i] + 1) for i in chosen_rel }

    # Build partitions: r_0 is anchor; transition i chosen => r_i delta in same partition
    partitions: List[List[int]] = []
    cur: List[int] = [0]
    for i in range(1, n):
        if i in chosen_transitions:
            cur.append(i)
        else:
            partitions.append(cur)
            cur = [i]
    if cur:
        partitions.append(cur)
    return chosen_transitions, partitions
