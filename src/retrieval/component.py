# src/retrieval/component.py
from __future__ import annotations
from enum import Enum

class ComponentType(str, Enum):
    ELECTROLYZER = "ELECTROLYZER"
    METAL_HYDRIDE = "METAL_HYDRIDE"
    FUEL_CELL = "FUEL_CELL"
    HEAT_PUMP = "HEAT_PUMP"
    DISTRICT_HEAT = "DISTRICT_HEAT"