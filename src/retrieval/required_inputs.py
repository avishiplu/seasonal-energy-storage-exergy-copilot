# src/retrieval/required_inputs.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from src.retrieval.component import ComponentType


@dataclass(frozen=True)
class RequiredInput:
    key: str
    unit: str
    critical: bool
    basis: str | None = None   # e.g., "LHV", "HHV", "thermal", "electric" (optional)
    notes: str | None = None   # optional human note


REQUIRED_INPUTS: dict[ComponentType, List[RequiredInput]] = {
    ComponentType.ELECTROLYZER: [
        RequiredInput(key="eta_el", unit="1", critical=True, basis="electric", notes="Electrical efficiency"),
        RequiredInput(key="p_out_Pa", unit="Pa", critical=True, notes="Outlet pressure"),
        RequiredInput(key="T_out_K", unit="K", critical=False, notes="Outlet temperature"),
    ],
    ComponentType.METAL_HYDRIDE: [
        RequiredInput(key="T_abs_K", unit="K", critical=True, basis="thermal", notes="Absorption temperature"),
        RequiredInput(key="T_des_K", unit="K", critical=True, basis="thermal", notes="Desorption temperature"),
        RequiredInput(key="Peq_Pa", unit="Pa", critical=True, notes="Equilibrium pressure (e.g., van’t Hoff)"),
    ],
    ComponentType.FUEL_CELL: [
        RequiredInput(key="eta_fc", unit="1", critical=True, basis="electric", notes="Electrical efficiency (fuel cell)"),
        RequiredInput(key="T_heat_K", unit="K", critical=True, basis="thermal", notes="Heat temperature level"),
    ],
    ComponentType.HEAT_PUMP: [
        RequiredInput(key="COP", unit="1", critical=True, basis="thermal", notes="Coefficient of performance"),
        RequiredInput(key="T_supply_K", unit="K", critical=True, notes="Supply temperature"),
        RequiredInput(key="T0_K", unit="K", critical=True, notes="Reference environment temperature"),
    ],
    ComponentType.DISTRICT_HEAT: [
        RequiredInput(key="Tb_K", unit="K", critical=True, basis="thermal", notes="Boundary temperature for heat exergy"),
        RequiredInput(key="T0_K", unit="K", critical=True, notes="Reference environment temperature"),
    ],
}


def required_inputs_for(component: ComponentType) -> List[RequiredInput]:
    return REQUIRED_INPUTS.get(component, [])
