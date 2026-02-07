from __future__ import annotations

from src.core.values import ValueSpec, computed_value
from src.core.validate_values import require_source
from src.core.refusal import RefusalError


def exergy_destruction_balance_full(
    Ex_in: ValueSpec,
    Ex_out: ValueSpec,
    W_in: ValueSpec | None = None,
    W_out: ValueSpec | None = None,
    Ex_loss: ValueSpec | None = None,
) -> ValueSpec:
    """
    Ex_dest = Ex_in + W_in - Ex_out - W_out - Ex_loss
    Refuse if negative beyond tolerance.
    """

    require_source(Ex_in)
    require_source(Ex_out)

    def _require_J(v: ValueSpec, name: str) -> None:
        require_source(v)
        if v.unit != "J":
            raise RefusalError(
                code="REFUSE_EXERGY_TERM_UNIT",
                user_message=f"Cannot compute because {name} is not in Joule (J).",
                why="All exergy/work terms must be in Joule for the balance.",
                missing=[f"{name}.unit=J"],
                details={"got_unit": v.unit},
            )

    _require_J(Ex_in, "Ex_in")
    _require_J(Ex_out, "Ex_out")

    total = float(Ex_in.value) - float(Ex_out.value)

    if W_in is not None:
        _require_J(W_in, "W_in")
        total += float(W_in.value)

    if W_out is not None:
        _require_J(W_out, "W_out")
        total -= float(W_out.value)

    if Ex_loss is not None:
        _require_J(Ex_loss, "Ex_loss")
        total -= float(Ex_loss.value)

    if total < -1e-9:
        raise RefusalError(
            code="REFUSE_NEGATIVE_EXERGY_DESTRUCTION",
            user_message="Cannot compute because exergy destruction becomes negative.",
            why="Second law violation or boundary mismatch.",
            details={"Ex_dest": total},
        )

    if total < 0:
        total = 0.0

    return computed_value(
        value=total,
        unit="J",
        tool_name="exergy_destruction_balance_full",
        meta={
            "inputs": {
                "Ex_in": Ex_in.value,
                "Ex_out": Ex_out.value,
                "W_in": None if W_in is None else W_in.value,
                "W_out": None if W_out is None else W_out.value,
                "Ex_loss": None if Ex_loss is None else Ex_loss.value,
            }
        },
    )
