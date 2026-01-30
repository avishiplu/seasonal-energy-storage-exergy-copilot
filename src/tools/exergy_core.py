from __future__ import annotations

from core.values import ValueSpec, computed_value
from core.validate_values import require_source


def thermal_exergy_of_heat(Q: ValueSpec, Tb_K: ValueSpec, T0_K: ValueSpec) -> ValueSpec:
    """
    Ex = Q * (1 - T0/Tb)

    Inputs (ValueSpec):
      Q    : heat energy (J)
      Tb_K : boundary temperature in Kelvin
      T0_K : reference environment temperature in Kelvin

    Output:
      ValueSpec (COMPUTED), unit="J"
    """

    # 1) Enforce source tagging
    require_source(Q)
    require_source(Tb_K)
    require_source(T0_K)

    # 2) Convert to floats for math + comparisons
    q = float(Q.value)
    tb = float(Tb_K.value)
    t0 = float(T0_K.value)

    # 3) Validations
    if q < 0:
        raise ValueError("Q must be >= 0")
    if tb <= 0 or t0 <= 0:
        raise ValueError("Temperatures must be > 0 K")
    if tb <= t0:
        raise ValueError("Tb_K must be > T0_K for exergy-of-heat shortcut")

    # 4) Compute
    ex = q * (1.0 - (t0 / tb))

    # 5) Return as computed ValueSpec with tool + input metadata
    return computed_value(
        value=ex,
        unit="J",
        tool_name="thermal_exergy_of_heat",
        meta={
            "inputs": {
                "Q": {"value": Q.value, "unit": Q.unit, "source_type": Q.source_type.value},
                "Tb_K": {"value": Tb_K.value, "unit": Tb_K.unit, "source_type": Tb_K.source_type.value},
                "T0_K": {"value": T0_K.value, "unit": T0_K.unit, "source_type": T0_K.source_type.value},
            }
        },
    )
