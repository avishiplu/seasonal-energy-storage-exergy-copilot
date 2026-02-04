from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import uuid

from src.core.values import ValueSpec
from src.core.validate_values import require_source
from src.core.refusal import RefusalError


@dataclass(frozen=True)
class Scenario:
    """
    Scenario = shared reference context for comparison.
    Phase 1.3: T0 must be explicit.
    Phase 2.5: scenario_id + scenario_version for traceability.
    Phase 3.4: analysis_intent required to drive agent priorities later.
    """
    name: str
    location: str
    time_start: str   # ISO format: "2024-01-01"
    time_end: str     # ISO format: "2024-12-31"

    # Traceability (immutable)
    scenario_id: str = field(default_factory=lambda: str(uuid.uuid4()), init=False)
    scenario_version: int = field(default=1, init=False)

    # Mandatory for exergy (Kelvin)
    T0_K: Optional[ValueSpec]        # Reference environment temperature

    # DH delivery boundary temps (Kelvin)
    Ts_K: Optional[ValueSpec] = None
    Tr_K: Optional[ValueSpec] = None

    # Phase 3.4 — NEW
    analysis_intent: Optional[str] = None  # comparison / feasibility / sensitivity / teaching


    def validate(self) -> None:
        # ---------------------------
        # Scenario version check
        # ---------------------------
        if self.scenario_version < 1:
            raise RefusalError(
                code="REFUSE_SCENARIO_VERSION_INVALID",
                user_message="Scenario version must be a positive integer (>= 1).",
                why="Scenario versioning is required for traceability and reproducibility of results.",
                missing=["scenario.scenario_version >= 1"],
                details={"scenario_version": self.scenario_version},
            )

        # ---------------------------
        # Location check
        # ---------------------------
        if not self.location:
            raise RefusalError(
                code="REFUSE_SCENARIO_LOCATION_MISSING",
                user_message="Cannot run scenario because location is missing.",
                why="Scenario must define a location so the comparison context is explicit.",
                missing=["scenario.location"],
            )

        # ---------------------------
        # Time range check
        # ---------------------------
        if not self.time_start or not self.time_end:
            raise RefusalError(
                code="REFUSE_SCENARIO_TIME_RANGE_MISSING",
                user_message="Cannot run scenario because time range is missing.",
                why="Scenario must define a start and end time range for the comparison context.",
                missing=["scenario.time_start", "scenario.time_end"],
            )

        # ---------------------------
        # T0 must exist
        # ---------------------------
        if self.T0_K is None:
            raise RefusalError(
                code="REFUSE_SCENARIO_T0_MISSING",
                user_message="Cannot run scenario because reference temperature T0 is missing.",
                why="Exergy calculations require an explicit reference environment temperature (T0).",
                missing=["scenario.T0_K"],
            )

        # T0 must have a source + must be Kelvin
        require_source(self.T0_K)
        if self.T0_K.unit != "K":
            raise RefusalError(
                code="REFUSE_SCENARIO_T0_UNIT",
                user_message="T0 must be provided in Kelvin (K).",
                why="Reference temperature must be in Kelvin for exergy calculations.",
                missing=["scenario.T0_K.unit = K"],
                details={"T0_unit": self.T0_K.unit},
            )

        # ---------------------------
        # Ts/Tr must exist (DH boundary is part of functional unit)
        # ---------------------------
        if self.Ts_K is None or self.Tr_K is None:
            raise RefusalError(
                code="REFUSE_SCENARIO_DH_TEMPS_MISSING",
                user_message="Cannot run scenario because DH supply/return temperatures (Ts, Tr) are missing.",
                why=(
                    "Functional unit defines the DH delivery boundary using Ts and Tr. "
                    "Without Ts/Tr, 'useful heat delivered to DH boundary' is not defined."
                ),
                missing=["scenario.Ts_K", "scenario.Tr_K"],
            )

        # Ts/Tr must be source-tagged
        require_source(self.Ts_K)
        require_source(self.Tr_K)

        # Ts/Tr must be Kelvin
        if self.Ts_K.unit != "K" or self.Tr_K.unit != "K":
            raise RefusalError(
                code="REFUSE_SCENARIO_DH_TEMP_UNITS",
                user_message="DH supply/return temperatures must be provided in Kelvin (K).",
                why="Ts and Tr must be in Kelvin for consistent boundary definition and exergy-safe temperature handling.",
                missing=["scenario.Ts_K.unit = K", "scenario.Tr_K.unit = K"],
                details={"Ts_unit": self.Ts_K.unit, "Tr_unit": self.Tr_K.unit},
            )

        # ---------------------------
        # Phase 3.4 — analysis intent required
        # ---------------------------
        allowed = {"comparison", "feasibility", "sensitivity", "teaching"}
        if self.analysis_intent not in allowed:
            raise RefusalError(
                code="REFUSE_SCENARIO_INTENT_MISSING",
                user_message="Cannot run scenario because analysis intent is missing or invalid.",
                why="Scenario must declare why the analysis is run so the agent can prioritize outputs and warnings.",
                missing=["scenario.analysis_intent in {comparison, feasibility, sensitivity, teaching}"],
                details={"got": self.analysis_intent, "allowed": sorted(list(allowed))},
            )


    def intent_flags(self) -> dict:
        """
        Structural helper for later agent/UI logic.
        No physics, no calculations.
        """
        intent = self.analysis_intent
        return {
            "intent": intent,
            "prioritize_comparison_tables": intent == "comparison",
            "prioritize_feasibility_warnings": intent == "feasibility",
            "prioritize_sensitivity_outputs": intent == "sensitivity",
            "prioritize_teaching_explanations": intent == "teaching",
        }
