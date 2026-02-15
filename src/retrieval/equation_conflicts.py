# src/retrieval/equation_conflicts.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from src.retrieval.equation_validator import EqTag


@dataclass
class TaggedEquation:
    name: str
    canonical: str
    tag: EqTag
    notes: str | None = None

    # --- rewrite metadata (spec 6.3B) ---
    rewrite_flag: bool = False
    original_equation: str | None = None
    rewrite_confidence: float | None = None


def _lhs_key(eq: str) -> str | None:
    if "=" not in eq:
        return None
    lhs = eq.split("=", 1)[0].strip()
    return re.sub(r"\s+", " ", lhs)


def cross_check_conflicts(eqs: List[TaggedEquation]) -> List[TaggedEquation]:
    by_lhs: Dict[str, List[TaggedEquation]] = {}
    for e in eqs:
        k = _lhs_key(e.canonical)
        if not k:
            continue
        by_lhs.setdefault(k, []).append(e)

    for lhs, items in by_lhs.items():
        rhs_set = set(i.canonical.split("=", 1)[1].strip() for i in items if "=" in i.canonical)
        if len(rhs_set) > 1:
            for it in items:
                it.tag = EqTag.CONFLICT
                it.notes = (it.notes or "") + f" CONFLICT: same LHS '{lhs}' has multiple RHS."
    return eqs
