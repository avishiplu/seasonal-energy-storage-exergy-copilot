from __future__ import annotations

from core.values import ValueSpec, computed_value
from core.validate_values import require_source
from core.guardrails import refuse_if_T0_missing, refuse_if_Tb_not_above_T0
from tools.units import refuse_if_unit_ambiguous_energy


def thermal_exergy_of_heat(
    Q: ValueSpec,
    Tb_K: ValueSpec,
    T0_K: ValueSpec | None,
) -> ValueSpec:
    """
    Exergy of heat:
    Ex = Q * (1 - T0 / Tb)

    Refusal rules:
    - Rule 0.4.1: refuse if T0 is missing
    - Rule 0.4.2: refuse if energy unit is ambiguous
    """

    # --- Rule 0.4.1 ---
    # If T0_K is None, this will raise RefusalError (NOT ValueError)
    refuse_if_T0_missing(T0_K)

    # After this line, we KNOW T0_K is not None
    assert T0_K is not None

    # Source validation
    require_source(Q)
    require_source(Tb_K)
    require_source(T0_K)

    # Temperature units
    if Tb_K.unit != "K" or T0_K.unit != "K":
        raise ValueError("Temperatures must be in Kelvin (K).")

    # --- Rule 0.4.2 ---
    refuse_if_unit_ambiguous_energy(Q)

    # This tool expects Joule
    if Q.unit != "J":
        raise ValueError("Q must be in Joule (J) for this tool.")

    Tb = float(Tb_K.value)
    T0 = float(T0_K.value)

    if Tb <= 0 or T0 <= 0:
        raise ValueError("Temperatures must be > 0 K.")

    refuse_if_Tb_not_above_T0(Tb_K=Tb_K, T0_K=T0_K)

    ex = float(Q.value) * (1.0 - T0 / Tb)

    return computed_value(
        value=ex,
        unit="J",
        tool_name="thermal_exergy_of_heat",
        meta={
            "inputs": {
                "Q": {"value": Q.value, "unit": Q.unit, "source": Q.source_type.value},
                "Tb_K": {"value": Tb_K.value, "unit": Tb_K.unit, "source": Tb_K.source_type.value},
                "T0_K": {"value": T0_K.value, "unit": T0_K.unit, "source": T0_K.source_type.value},
            }
        },
    )
