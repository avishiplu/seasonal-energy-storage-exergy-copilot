from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FunctionalUnit:
    """
    Frozen comparison basis.
    """
    delivered_heat_MWh: float
    description: str


@dataclass(frozen=True)
class DHBoundarySpec:
    """
    Delivery boundary specification (units only).
    Actual Ts/Tr values belong to Scenario config later (Phase 2),
    but the boundary meaning is frozen here.
    """
    name: str
    Ts_unit: str = "K"
    Tr_unit: str = "K"


# Single source of truth (Phase 1.1)
FUNCTIONAL_UNIT = FunctionalUnit(
    delivered_heat_MWh=1.0,
    description="1 MWh useful heat delivered to DH delivery boundary",
)

DH_BOUNDARY_SPEC = DHBoundarySpec(
    name="district_heating_delivery_boundary"
)
