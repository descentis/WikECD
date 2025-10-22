from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Optional, Protocol

@dataclass(frozen=True)
class Revision:
    revid: int
    timestamp: str
    text: str

    @property
    def size(self) -> int:
        return len(self.text)

class RevisionSource(Protocol):
    def get_revisions(self, *, title: Optional[str] = None) -> Iterable[Revision]:
        ...
