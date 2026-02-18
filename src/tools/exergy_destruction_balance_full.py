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

    Robust rule:
    - allow tiny negative due to floating noise -> clamp to 0
    - refuse only if negative beyond tolerance (abs + relative)
    """

    def _require_J(v: ValueSpec, name: str) -> None:
        require_source(v)
        if v.unit != "J":
            raise RefusalError(
                code="REFUSE_EXERGY_TERM_UNIT",
                user_message=f"Cannot compute because {name} is not in Joule (J).",
                why="All exergy/work terms must be in Joule for the balance.",
                missing=[f"{name}.unit=J"],
                details={"term": name, "got_unit": v.unit},
            )

    _require_J(Ex_in, "Ex_in")
    _require_J(Ex_out, "Ex_out")

    ex_in = float(Ex_in.value)
    ex_out = float(Ex_out.value)
    w_in = 0.0
    w_out = 0.0
    ex_loss = 0.0

    if W_in is not None:
        _require_J(W_in, "W_in")
        w_in = float(W_in.value)

    if W_out is not None:
        _require_J(W_out, "W_out")
        w_out = float(W_out.value)

    if Ex_loss is not None:
        _require_J(Ex_loss, "Ex_loss")
        ex_loss = float(Ex_loss.value)

    total_raw = ex_in + w_in - ex_out - w_out - ex_loss

    # tolerance: absolute + relative (scale-aware)
    abs_tol = 1e-6
    rel_tol = 1e-9 * max(1.0, abs(ex_in), abs(ex_out), abs(w_in), abs(w_out), abs(ex_loss))
    tol = max(abs_tol, rel_tol)

    if total_raw < -tol:
        raise RefusalError(
            code="REFUSE_NEGATIVE_EXERGY_DESTRUCTION",
            user_message="Cannot compute because exergy destruction becomes negative.",
            why="Second law violation, boundary mismatch, or bookkeeping inconsistency beyond tolerance.",
            missing=[],
            details={
                "Ex_in_J": ex_in,
                "Ex_out_J": ex_out,
                "W_in_J": w_in,
                "W_out_J": w_out,
                "Ex_loss_J": ex_loss,
                "Ex_dest_raw_J": total_raw,
                "tolerance_J": tol,
            },
        )

    total = 0.0 if total_raw < 0.0 else total_raw

    return computed_value(
        value=total,
        unit="J",
        tool_name="exergy_destruction_balance_full",
        meta={
            "inputs": {
                "Ex_in": ex_in,
                "Ex_out": ex_out,
                "W_in": w_in if W_in is not None else None,
                "W_out": w_out if W_out is not None else None,
                "Ex_loss": ex_loss if Ex_loss is not None else None,
            },
            "tolerance_J": tol,
            "clamped": total_raw < 0.0,
        },
    )
