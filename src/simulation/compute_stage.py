from __future__ import annotations

from src.simulation.stage import Stage, StageType
from src.core.scenario import Scenario
from src.core.refusal import RefusalError

from src.tools.exergy_core import thermal_exergy_of_heat


def compute_stage(stage: Stage, scenario: Scenario) -> Stage:
    """
    Compute stage-level computed fields using deterministic tools.
    Returns a NEW Stage with updated .computed (Stage is frozen).
    """

    computed = dict(stage.computed)

    # Minimal implementation: DELIVER stage exergy of delivered heat
    if stage.stage_type == StageType.DELIVER:
        Q = stage.inputs.get("heat_in")
        Tb = stage.Tb_K

        if Q is None or Tb is None:
            raise RefusalError(
                code="REFUSE_STAGE_DELIVER_INPUTS_MISSING",
                user_message="Cannot compute DELIVER stage because required inputs are missing.",
                why="DELIVER stage requires heat_in and Tb_K to compute exergy of delivered heat.",
                missing=["stage.inputs.heat_in", "stage.Tb_K"],
            )

        Ex_out = thermal_exergy_of_heat(Q=Q, Tb_K=Tb, T0_K=scenario.T0_K)
        computed["Ex_out"] = Ex_out

    # Return new Stage (because Stage is frozen)
    return Stage(
        name=stage.name,
        stage_type=stage.stage_type,
        inputs=stage.inputs,
        outputs=stage.outputs,
        losses=stage.losses,
        Tb_K=stage.Tb_K,
        computed=computed,
    )
