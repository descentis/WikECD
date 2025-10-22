from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any

@dataclass
class CompressedArticle:
    """
    Representation:
      - anchors: list of base revision indices (0-based)
      - patches: dict[(i-1, i)] -> ndiff lines from rev(i-1) to rev(i) for edges that are inside partitions
      - meta: can include partitions, counts, etc.
    NOTE: Actual base texts are not stored here; caller should persist them externally
          or embed them (choose what fits your pipeline). For now we store them next to `meta` if needed.
    """
    title: str
    anchors: List[int]
    patches: Dict[Tuple[int, int], List[str]]
    meta: Dict[str, Any] = field(default_factory=dict)

    def partitions(self) -> List[List[int]]:
        return self.meta.get("partitions", [])
