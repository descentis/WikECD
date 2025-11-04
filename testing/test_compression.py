from pathlib import Path
import pytest

from WikECD.compression.diff_utils import approx_diffs_from_sizes
from WikECD.compression.knapsack import knapsack  # your exact dp solver
from WikECD.compression.knapsack_heuristic import heuristic_knapsack
from WikECD.compression.partitioner import optimal_partition_indices


def test_approx_diffs_and_values():
    sizes = [1, 2, 8]
    diffs = approx_diffs_from_sizes(sizes)
    # with approx doubling rule: diffs ~ 2*|delta|
    assert len(diffs) == 2
    assert diffs[0] == 2 * abs(sizes[1] - sizes[0])


def test_knapsack_consistency_small():
    values = [5, 4, 3]
    weights = [3, 2, 2]
    cap = 4
    exact = set(knapsack(values, weights, cap))
    heuristic = set(heuristic_knapsack(values, weights, cap, strategy="auto"))
    # heuristic should be valid (weights <= cap)
    assert sum(weights[i] for i in heuristic) <= cap
    # heuristic should produce value >= 0
    assert sum(values[i] for i in heuristic) >= 0
    # exact should be optimal
    exact_val = sum(values[i] for i in exact)
    hval = sum(values[i] for i in heuristic)
    assert hval <= exact_val


def test_partitioner_basic():
    sizes = [1,2,8]
    chosen_transitions, partitions = optimal_partition_indices(sizes, time_budget=9, solver="heuristic", strategy="greedy")
    assert isinstance(partitions, list)
    # partitions should cover all indices
    covered = sum(len(p) for p in partitions)
    assert covered == len(sizes)
