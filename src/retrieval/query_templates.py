# src/retrieval/query_templates.py
from __future__ import annotations

from typing import List

KEY_TO_TERMS = {
    "eta_el": ["electrical efficiency", "efficiency"],
    "p_out_Pa": ["outlet pressure", "hydrogen outlet pressure", "delivery pressure"],
    "T_out_K": ["outlet temperature", "operating temperature"],

    # PTES
    "eta_collector": ["collector efficiency", "solar collector efficiency", "optical efficiency"],
    "A_collector_m2": ["collector area", "aperture area", "A_collector"],
    "G_solar_Wm2": ["solar irradiance", "global irradiance", "G_solar"],
    "t_operation_s": ["operation time", "collection time", "t_operation"],
    "UA_WK": ["overall heat loss coefficient", "UA", "heat loss coefficient"],
    "T_store_K": ["storage temperature", "T_store"],
    "t_storage_s": ["storage duration", "storage time", "t_storage"],
    "COP": ["COP", "coefficient of performance"],
    "T_supply_K": ["supply temperature", "district heating supply temperature", "T_supply"],
    "Tb_K": ["boundary temperature", "delivery temperature", "Tb"],
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
