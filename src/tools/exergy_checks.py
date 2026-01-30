from __future__ import annotations

from core.values import ValueSpec, computed_value
from core.refusal import RefusalError
from core.validate_values import require_source


def exergy_destruction_balance(Ex_in: ValueSpec, Ex_out: ValueSpec) -> ValueSpec:
    """
    Ex_destr = Ex_in - Ex_out

    Rule 0.4.3:
    Refuse if exergy destruction becomes negative.
    """
    # Ensure inputs are valid ValueSpec with source metadata
    require_source(Ex_in)
    require_source(Ex_out)

    # Exergy balance must be done in Joule
    if Ex_in.unit != "J" or Ex_out.unit != "J":
        raise RefusalError(
            code="REFUSE_UNIT_WRONG_FOR_EXERGY",
            user_message="Cannot compute because exergy unit is not Joule (J).",
            why=(
                "Exergy destruction balance requires both Ex_in and Ex_out "
                "to be expressed in Joule (J)."
            ),
            missing=["Ex_in.unit=J", "Ex_out.unit=J"],
        )

    # Compute destruction
    ex_destr = float(Ex_in.value) - float(Ex_out.value)

    # Negative beyond numerical noise => physical impossibility
    if ex_destr < -1e-9:
        raise RefusalError(
            code="REFUSE_NEGATIVE_EXERGY_DESTRUCTION",
            user_message="Cannot compute because exergy destruction becomes negative.",
            why=(
                "According to the second law of thermodynamics, exergy destruction "
                "can never be negative. This indicates a boundary or definition mismatch."
            ),
            details={
                "Ex_in": Ex_in.value,
                "Ex_out": Ex_out.value,
                "Ex_destr": ex_destr,
            },
        )

    # Clamp tiny numerical negatives to zero
    if ex_destr < 0:
        ex_destr = 0.0

    return computed_value(
        value=ex_destr,
        unit="J",
        tool_name="exergy_destruction_balance",
        meta={
            "inputs": {
                "Ex_in": {
                    "value": Ex_in.value,
                    "unit": Ex_in.unit,
                    "source": Ex_in.source_type.value,
                },
                "Ex_out": {
                    "value": Ex_out.value,
                    "unit": Ex_out.unit,
                    "source": Ex_out.source_type.value,
                },
            }
        },
    )
