from __future__ import annotations

from typing import Optional

from core.values import ValueSpec
from core.refusal import RefusalError


def refuse_if_T0_missing(T0_K: Optional[ValueSpec]) -> None:
    """
    Rule 0.4.1:
    Refuse computation if reference environment temperature (T0) is missing.
    """
    if T0_K is None:
        raise RefusalError(
            code="REFUSE_T0_MISSING",
            user_message="Cannot compute because reference temperature (T0) is missing.",
            why=(
                "Exergy calculations require a reference environment temperature (T0). "
                "Without T0, second-law-consistent results are not possible."
            ),
            missing=["T0_K"],
        )


def refuse_if_delivery_boundary_missing(delivery_boundary: Optional[dict]) -> None:
    """
    Rule 0.4.4:
    Refuse computation if delivery boundary is missing or incomplete.

    Delivery boundary defines where the system delivers its 'useful output'.
    """
    if not delivery_boundary or not isinstance(delivery_boundary, dict):
        raise RefusalError(
            code="REFUSE_DELIVERY_BOUNDARY_MISSING",
            user_message="Cannot compute because the system delivery boundary is not defined.",
            why=(
                "To compare systems fairly, all systems must define the same "
                "'useful output boundary'. Without it, comparisons are invalid."
            ),
            missing=["delivery_boundary"],
        )

    if not delivery_boundary.get("name"):
        raise RefusalError(
            code="REFUSE_DELIVERY_BOUNDARY_NAME_MISSING",
            user_message="Cannot compute because the delivery boundary has no name or label.",
            why=(
                "Without a delivery boundary name, it is unclear which output "
                "is considered the useful system output."
            ),
            missing=["delivery_boundary.name"],
        )


def refuse_if_Tb_not_above_T0(Tb_K: ValueSpec, T0_K: ValueSpec) -> None:
    """
    Phase 1.4 validity rule:
    Exergy-of-heat shortcut requires Tb > T0.
    """
    from core.validate_values import require_source

    require_source(Tb_K)
    require_source(T0_K)

    if Tb_K.unit != "K" or T0_K.unit != "K":
        raise RefusalError(
            code="REFUSE_TEMP_UNIT_NOT_K",
            user_message="Cannot compute because temperature unit is not Kelvin (K).",
            why="Tb and T0 must be provided in Kelvin for exergy calculations.",
            missing=["Tb_K.unit=K", "T0_K.unit=K"],
        )

    Tb = float(Tb_K.value)
    T0 = float(T0_K.value)

    if Tb <= T0:
        raise RefusalError(
            code="REFUSE_TB_BELOW_OR_EQUAL_T0",
            user_message="Cannot compute exergy of heat because Tb is not above T0.",
            why="Shortcut Ex = Q*(1 - T0/Tb) requires Tb > T0.",
            missing=["Tb_K > T0_K"],
            details={"Tb_K": Tb, "T0_K": T0},
        )
