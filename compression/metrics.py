# WikECD/compression/metrics.py
from __future__ import annotations
from typing import List

def space_cost_from_partitions(sizes: List[int], partitions: List[List[int]]) -> int:
    total = 0
    for part in partitions:
        if not part:
            continue
        if len(part) == 1:
            i = part[0]
            total += sizes[i]
        else:
            l = part[0]
            total += sizes[l]
            for a, b in zip(part, part[1:]):
                total += abs(sizes[b] - sizes[a])
    return int(total)

def time_cost_from_partitions(sizes: List[int], partitions: List[List[int]]) -> int:
    total = 0
    for part in partitions:
        if not part:
            continue
        if len(part) == 1:
            total += 1
        else:
            subtotal = 1
            for a, b in zip(part, part[1:]):
                subtotal += sizes[a] + abs(sizes[b] - sizes[a])
            total += subtotal
    return int(total)

def orig_size_from_sizes(sizes: List[int]) -> int:
    return int(sum(sizes))
