from __future__ import annotations

from core.values import ValueSpec
from core.refusal import RefusalError
from core.validate_values import require_source


def refuse_if_unit_ambiguous_energy(v: ValueSpec) -> None:
    """
    Rule 0.4.2:
    Refuse if energy unit is ambiguous (MWh/kWh/Wh must declare thermal vs electric).

    Policy:
    - If unit is 'MWh' or 'kWh' or 'Wh' and meta does NOT contain:
      meta['energy_kind'] = 'thermal' or 'electric'
      => REFUSE
    """
    require_source(v)

    unit = (v.unit or "").strip()
    if unit in {"MWh", "kWh", "Wh"}:
        meta = v.meta or {}
        kind = meta.get("energy_kind")
        if kind not in {"thermal", "electric"}:
            raise RefusalError(
                code="REFUSE_UNIT_AMBIGUOUS",
                user_message=f"Cannot compute because '{unit}' is ambiguous (thermal vs electric is unknown).",
                why=(
                    "If you provide MWh/kWh/Wh, you must declare whether it is thermal energy or electric energy. "
                    "Otherwise efficiency chains and exergy results can be wrong."
                ),
                missing=[f"{unit}.meta.energy_kind"],
                details={"unit": unit, "required": ["meta.energy_kind = thermal/electric"]},
            )
