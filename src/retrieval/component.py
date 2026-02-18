from __future__ import annotations
from enum import Enum

class ComponentType(str, Enum):
    ELECTROLYZER = "ELECTROLYZER"
    METAL_HYDRIDE = "METAL_HYDRIDE"
    FUEL_CELL = "FUEL_CELL"
    HEAT_PUMP = "HEAT_PUMP"
    PTES = "PTES"
    DISTRICT_HEAT = "DISTRICT_HEAT"
