from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.values import ValueSpec
from core.validate_values import require_source
from core.refusal import RefusalError


@dataclass(frozen=True)
class Scenario:
    """
    Scenario = shared reference context for comparison.
    Phase 1.3: T0 must be explicit.
    """
    name: str
    T0_K: Optional[ValueSpec]        # Reference environment temperature
    Ts_K: Optional[ValueSpec] = None
    Tr_K: Optional[ValueSpec] = None

    def validate(self) -> None:
        # --- T0 must exist ---
        if self.T0_K is None:
            raise RefusalError(
                code="REFUSE_SCENARIO_T0_MISSING",
                user_message="Cannot run scenario because reference temperature T0 is missing.",
                why="Exergy calculations require an explicit reference environment temperature (T0).",
                missing=["scenario.T0_K"],
            )

        # --- T0 must be source-tagged ---
        require_source(self.T0_K)

        # --- T0 must be Kelvin ---
        if self.T0_K.unit != "K":
            raise RefusalError(
                code="REFUSE_SCENARIO_T0_UNIT",
                user_message="T0 must be provided in Kelvin (K).",
                why="Reference temperature must be in Kelvin for exergy calculations.",
                missing=["scenario.T0_K.unit = K"],
            )
