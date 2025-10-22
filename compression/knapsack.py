from __future__ import annotations
from typing import List, Tuple

def knapsack(values: List[int], weights: List[int], capacity: int) -> List[int]:
    """
    0/1 knapsack solver (DP). Returns chosen item indices (0-based).
    values/weights are for transitions (length m). capacity is time budget C.
    """
    n = len(values)
    if n == 0 or capacity <= 0:
        return []

    dp = [[0]*(capacity+1) for _ in range(n+1)]
    for i in range(1, n+1):
        v, w = values[i-1], weights[i-1]
        for cap in range(capacity+1):
            if w <= cap:
                dp[i][cap] = max(v + dp[i-1][cap-w], dp[i-1][cap])
            else:
                dp[i][cap] = dp[i-1][cap]

    # backtrack
    chosen: List[int] = []
    cap = capacity
    for i in range(n, 0, -1):
        if dp[i][cap] != dp[i-1][cap]:
            chosen.append(i-1)
            cap -= weights[i-1]
    chosen.reverse()
    return chosen
