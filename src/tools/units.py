from __future__ import annotations

from src.core.values import ValueSpec
from src.core.refusal import RefusalError
from src.core.validate_values import require_source

# ---------------------------
# PHASE 3 — Units + Safety Tools
# File: src/tools/units.py
# ---------------------------

# Energy conversion constants
WH_TO_J = 3600.0
KWH_TO_J = 3.6e6
MWH_TO_J = 3.6e9


# ---------------------------
# 0.4.2 (existing rule) — Ambiguous energy unit guard
# Keep this for backward compatibility.
# Phase 3 expands allowed energy_kind: thermal/electric/LHV/HHV.
# ---------------------------
def refuse_if_unit_ambiguous_energy(v: ValueSpec) -> None:
    """
    Rule 0.4.2:
    Refuse if energy unit is ambiguous (MWh/kWh/Wh must declare basis).

    Phase 3 update:
    - energy_kind can be: thermal / electric / LHV / HHV
    """
    require_source(v)

    unit = (v.unit or "").strip()
    if unit in {"MWh", "kWh", "Wh"}:
        meta = v.meta or {}
        kind = meta.get("energy_kind")
        allowed = {"thermal", "electric", "LHV", "HHV"}
        if kind not in allowed:
            raise RefusalError(
                code="REFUSE_UNIT_AMBIGUOUS",
                user_message=f"Cannot compute because '{unit}' is ambiguous (basis is unknown).",
                why=(
                    "If you provide MWh/kWh/Wh, you must declare whether it is thermal energy, electric energy, "
                    "or chemical energy basis (LHV/HHV). Otherwise results can be wrong."
                ),
                missing=["meta.energy_kind"],
                details={"unit": unit, "allowed": sorted(list(allowed)), "got": kind},
            )


# ---------------------------
# TASK 3.1 — Temperature tools
# ---------------------------
def convert_C_to_K(value: float) -> float:
    return float(value) + 273.15


def validate_kelvin_positive(K: float) -> None:
    if float(K) <= 0:
        raise RefusalError(
            code="REFUSE_TEMPERATURE_NOT_POSITIVE",
            user_message="Temperature must be greater than 0 Kelvin.",
            why="Absolute temperature in Kelvin cannot be zero or negative.",
            missing=["T > 0 K"],
            details={"value": K},
        )


def normalize_temperature_to_K(v: ValueSpec) -> ValueSpec:
    """
    Accept temperature in K or °C and return a ValueSpec in Kelvin.
    Refuse unknown units or non-physical temperatures (K <= 0).

    - preserves: source_type, citation, meta
    - does NOT mutate input
    """
    require_source(v)

    unit = (v.unit or "").strip()

    if unit == "K":
        validate_kelvin_positive(float(v.value))
        return v

    if unit in {"C", "°C"}:
        K = convert_C_to_K(float(v.value))
        validate_kelvin_positive(K)
        return ValueSpec(
            value=K,
            unit="K",
            source_type=v.source_type,
            citation=v.citation,
            meta=v.meta,
        )

    raise RefusalError(
        code="REFUSE_TEMP_UNIT_UNKNOWN",
        user_message="Cannot compute because temperature unit is unknown (expected K or °C).",
        why="Temperature must be provided in Kelvin (K) or Celsius (°C) so it can be normalized safely.",
        missing=["temperature.unit in {K, °C}"],
        details={"unit": unit},
    )


# ---------------------------
# TASK 3.2 — Energy tools
# ---------------------------
def require_energy_kind(v: ValueSpec) -> None:
    """
    Enforce basis label:
    - thermal
    - electric
    - LHV
    - HHV
    """
    require_source(v)
    meta = v.meta or {}
    kind = meta.get("energy_kind")
    allowed = {"thermal", "electric", "LHV", "HHV"}
    if kind not in allowed:
        raise RefusalError(
            code="REFUSE_ENERGY_KIND_MISSING",
            user_message="Energy basis must be declared (thermal / electric / LHV / HHV).",
            why="Energy quantities in Wh/kWh/MWh are ambiguous without an explicit basis label.",
            missing=["meta.energy_kind"],
            details={"allowed": sorted(list(allowed)), "got": kind},
        )


def convert_energy_to_J(v: ValueSpec) -> ValueSpec:
    """
    Convert energy to Joule if unit is Wh/kWh/MWh.
    - For J: return as-is
    - For other units: return as-is (NO guessing)

    Phase 3 rule:
    If unit is Wh/kWh/MWh => meta.energy_kind is mandatory.
    """
    require_source(v)

    unit = (v.unit or "").strip()

    # enforce basis for convertible "energy" units
    if unit in {"Wh", "kWh", "MWh"}:
        require_energy_kind(v)

    if unit == "J":
        return v

    if unit == "Wh":
        return ValueSpec(
            value=float(v.value) * WH_TO_J,
            unit="J",
            source_type=v.source_type,
            citation=v.citation,
            meta=v.meta,
        )

    if unit == "kWh":
        return ValueSpec(
            value=float(v.value) * KWH_TO_J,
            unit="J",
            source_type=v.source_type,
            citation=v.citation,
            meta=v.meta,
        )

    if unit == "MWh":
        return ValueSpec(
            value=float(v.value) * MWH_TO_J,
            unit="J",
            source_type=v.source_type,
            citation=v.citation,
            meta=v.meta,
        )

    # Unknown / non-convertible unit: do nothing (refusal belongs in tool that requires J)
    return v
