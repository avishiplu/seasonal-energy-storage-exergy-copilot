# src/retrieval/query_templates.py
from __future__ import annotations

from typing import List

KEY_TO_TERMS = {
    "eta_el": ["electrical efficiency", "efficiency"],
    "p_out_Pa": ["outlet pressure", "hydrogen outlet pressure", "delivery pressure"],
    "T_out_K": ["outlet temperature", "operating temperature"],
}


def build_queries(component_label: str, quantity_key: str) -> List[str]:
    terms = KEY_TO_TERMS.get(quantity_key, [quantity_key])

    variants: List[str] = []

    for t in terms:
        variants += [
            f"{component_label} {t} equation",
            f"{component_label} {t} formula",
            f"{component_label} {t} definition",
        ]

    # de-duplicate while preserving order
    seen = set()
    out: List[str] = []
    for s in variants:
        if s not in seen:
            seen.add(s)
            out.append(s)

    return out
