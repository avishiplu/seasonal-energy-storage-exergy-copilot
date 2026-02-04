from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

from src.core.values import ValueSpec


class StageType(str, Enum):
    CHARGE = "CHARGE"
    STORE = "STORE"
    CONVERT = "CONVERT"
    DELIVER = "DELIVER"
    AUX = "AUX"


@dataclass(frozen=True)
class Stage:
    name: str
    stage_type: StageType
    inputs: Dict[str, ValueSpec] = field(default_factory=dict)
    outputs: Dict[str, ValueSpec] = field(default_factory=dict)
    losses: Dict[str, ValueSpec] = field(default_factory=dict)
    Tb_K: Optional[ValueSpec] = None
    computed: Dict[str, ValueSpec] = field(default_factory=dict)
