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
