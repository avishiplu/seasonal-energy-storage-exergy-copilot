# src/retrieval/missing_report.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


class InfoStatus(str, Enum):
    FOUND = "FOUND"
    MISSING = "MISSING"
    PARTIAL = "PARTIAL"
    AMBIGUOUS = "AMBIGUOUS"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class InfoItem:
    key: str
    unit: str
    status: InfoStatus
    critical: bool
    why: Optional[str] = None
    citation_pdf: Optional[str] = None
    citation_page: Optional[int] = None


@dataclass(frozen=True)
class MissingInformationReport:
    component: str
    items: List[InfoItem]

    def sorted_items(self) -> List[InfoItem]:
        # Priority: critical first
        return sorted(self.items, key=lambda x: (not x.critical, x.key))
