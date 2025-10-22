from __future__ import annotations
from typing import List, Tuple, Dict


def _chosen_indices_from_mask(mask: List[bool]) -> List[int]:
    return [i for i, b in enumerate(mask) if b]


# ------------------------------------------------------------
# Greedy by value/weight ratio + single-item check + 1-swap
# ------------------------------------------------------------
def greedy_ratio(values: List[int], weights: List[int], capacity: int, improve: bool = True) -> List[int]:
    n = len(values)
    if n == 0 or capacity <= 0:
        return []
    order = sorted(range(n), key=lambda i: (values[i] / weights[i]) if weights[i] else float('inf'), reverse=True)

    chosen: List[int] = []
    total_w = 0
    best_single = max((i for i in range(n) if weights[i] <= capacity), key=lambda i: values[i], default=None)
    for i in order:
        w = weights[i]
        if total_w + w <= capacity:
            chosen.append(i)
            total_w += w

    # Compare against best single item
    def value_of(ixs: List[int]) -> int:
        return sum(values[i] for i in ixs)
    best = chosen
    if best_single is not None and value_of([best_single]) > value_of(best):
        best = [best_single]

    if not improve or not best:
        return sorted(best)

    # 1-swap improvement: try replacing one chosen with one unchosen
    chosen_set = set(best)
    total_w = sum(weights[i] for i in best)
    best_val = value_of(best)
    improved = True
    while improved:
        improved = False
        for out_i in list(chosen_set):
            for in_i in range(n):
                if in_i in chosen_set:
                    continue
                new_w = total_w - weights[out_i] + weights[in_i]
                if new_w <= capacity:
                    new_val = best_val - values[out_i] + values[in_i]
                    if new_val > best_val:
                        chosen_set.remove(out_i)
                        chosen_set.add(in_i)
                        total_w = new_w
                        best_val = new_val
                        improved = True
                        break
            if improved:
                break
    return sorted(chosen_set)


# ------------------------------------------------------------
# FPTAS: (1 - eps) approximation via value scaling
# Time: O(n * V'), V' = sum scaled values; Memory: O(V')
# ------------------------------------------------------------
def fptas(values: List[int], weights: List[int], capacity: int, eps: float = 0.1) -> List[int]:
    n = len(values)
    if n == 0 or capacity <= 0:
        return []
    vmax = max(values) if values else 0
    if vmax == 0:
        return []
    K = max(1, int(eps * vmax / n))  # scaling factor
    scaled = [v // K for v in values]
    if sum(scaled) == 0:
        # scaling collapsed values; fall back to greedy
        return greedy_ratio(values, weights, capacity)

    # dp[v] = min weight to get scaled value sum exactly v; also keep choice backpointers sparsely
    INF = 10**18
    Vsum = sum(scaled)
    dp = [INF] * (Vsum + 1)
    dp[0] = 0
    parent = [(-1, -1)] * (Vsum + 1)  # (prev_value, taken_index)

    for i in range(n):
        sv, w = scaled[i], weights[i]
        # iterate backwards to avoid reuse
        for v in range(Vsum, sv - 1, -1):
            if dp[v - sv] + w < dp[v]:
                dp[v] = dp[v - sv] + w
                parent[v] = (v - sv, i)

    # find best v within capacity
    best_v = max((v for v in range(Vsum + 1) if dp[v] <= capacity), default=0)
    # backtrack
    chosen = []
    cur = best_v
    while cur > 0 and parent[cur][0] != -1:
        prev_v, idx = parent[cur]
        chosen.append(idx)
        cur = prev_v
    return sorted(set(chosen))


# ------------------------------------------------------------
# Sparse DP with dominance pruning
# State: map weight -> (value, chosen_indices_bitset or parent backpointers)
# Bound state size via pruning; often exact quickly in practice.
# ------------------------------------------------------------
def sparse_dp(values: List[int], weights: List[int], capacity: int, max_states: int = 100_000) -> List[int]:
    n = len(values)
    if n == 0 or capacity <= 0:
        return []

    # Each layer is dict weight->(value, parent_weight, chosen_index)
    layers: List[Dict[int, Tuple[int, int, int]]] = []
    cur: Dict[int, Tuple[int, int, int]] = {0: (0, -1, -1)}  # weight 0 -> (value 0, parent=-1, idx=-1)
    layers.append(cur)

    for i in range(n):
        v, w = values[i], weights[i]
        nxt: Dict[int, Tuple[int, int, int]] = dict(cur)  # skipping i keeps existing states

        for wt, (val, _, __) in cur.items():
            nwt = wt + w
            if nwt > capacity:
                continue
            nval = val + v
            prev = nxt.get(nwt)
            if (prev is None) or (nval > prev[0]):
                nxt[nwt] = (nval, wt, i)

        # Dominance pruning: sort by weight, keep states with strictly increasing value
        items = sorted(nxt.items())  # by weight
        pruned: Dict[int, Tuple[int, int, int]] = {}
        best_val = -1
        for wt, tup in items:
            if tup[0] > best_val:
                pruned[wt] = tup
                best_val = tup[0]

        # limit number of states to control memory
        if len(pruned) > max_states:
            # keep uniformly spaced weights to thin states
            step = max(1, len(pruned) // max_states)
            pruned = {wt: pruned[wt] for idx, wt in enumerate(pruned.keys()) if idx % step == 0}

        cur = pruned
        layers.append(cur)

    # best feasible
    best_w, (best_val, parent_w, idx) = max(cur.items(), key=lambda kv: kv[1][0])
    # backtrack
    chosen = []
    layer_idx = len(layers) - 1
    wcur = best_w
    while layer_idx > 0:
        state = layers[layer_idx].get(wcur)
        if state is None:
            # move up
            layer_idx -= 1
            continue
        val, parent_w, pick_idx = state
        if pick_idx != -1:
            chosen.append(pick_idx)
            wcur = parent_w
        layer_idx -= 1
    return sorted(set(chosen))


# ------------------------------------------------------------
# Strategy selector
# ------------------------------------------------------------
def heuristic_knapsack(
    values: List[int],
    weights: List[int],
    capacity: int,
    strategy: str = "auto",
    eps: float = 0.1,
    max_states: int = 100_000
) -> List[int]:
    """
    Strategies:
      - 'greedy'      : ratio greedy + single best + 1-swap
      - 'fptas'       : (1 - eps) approximation (value scaling)
      - 'sparse'      : sparse DP with dominance pruning
      - 'auto'        : pick based on problem shape
    """
    n = len(values)
    if strategy == "greedy":
        return greedy_ratio(values, weights, capacity, improve=True)
    if strategy == "fptas":
        return fptas(values, weights, capacity, eps=eps)
    if strategy == "sparse":
        return sparse_dp(values, weights, capacity, max_states=max_states)
    # auto: quick heuristic
    if n <= 200 and capacity <= 200_000:
        # sparse DP tends to be very good here
        return sparse_dp(values, weights, capacity, max_states=max_states)
    if n >= 2000:
        # go for FPTAS to bound time/memory
        return fptas(values, weights, capacity, eps=eps)
    # default: greedy + 1-swap
    return greedy_ratio(values, weights, capacity, improve=True)
