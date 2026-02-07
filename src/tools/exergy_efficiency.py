from __future__ import annotations

from src.core.values import ValueSpec, computed_value
from src.core.validate_values import require_source
from src.core.refusal import RefusalError


def exergy_efficiency(Ex_out: ValueSpec, Ex_in: ValueSpec) -> ValueSpec:
    """
    eta = Ex_out / Ex_in
    Deterministic tool: agent/UI must NOT compute this inline.
    """

    require_source(Ex_out)
    require_source(Ex_in)

    if Ex_out.unit != "J" or Ex_in.unit != "J":
        raise RefusalError(
            code="REFUSE_EXERGY_UNIT_NOT_J",
            user_message="Cannot compute exergy efficiency because units are not Joule (J).",
            why="Exergy efficiency requires Ex_out and Ex_in in Joule (J).",
            missing=["Ex_out.unit=J", "Ex_in.unit=J"],
        )

    ex_in = float(Ex_in.value)
    ex_out = float(Ex_out.value)

    if ex_in <= 0:
        raise RefusalError(
            code="REFUSE_EXERGY_INPUT_NONPOSITIVE",
            user_message="Cannot compute exergy efficiency because Ex_in <= 0.",
            why="Efficiency requires a positive exergy input.",
            missing=["Ex_in > 0"],
            details={"Ex_in": ex_in},
        )

    eta = ex_out / ex_in

    meta = {"inputs": {"Ex_out": ex_out, "Ex_in": ex_in}}
    if eta < 0 or eta > 1.2:
        meta["warning"] = "Exergy efficiency outside expected range; check boundary/definitions."

    return computed_value(
        value=eta,
        unit="-",
        tool_name="exergy_efficiency",
        meta=meta,
    )
