# src/simulation/build_stage_chain_minimal.py
from __future__ import annotations

from src.core.values import ValueSpec, assumption_value
from src.simulation.stage import Stage, StageType
from src.simulation.stage_chain import StageChain


def build_minimal_stage_chain(
    heat_delivered_J: ValueSpec,
    Tb_K: ValueSpec,
) -> StageChain:
    """
    Minimal, physics-valid StageChain (Phase 7 demo).

    IMPORTANT:
    - DELIVER stage MUST provide exergy output via stage.outputs so that
      compute_stage() produces computed['Ex_out_total'] > 0.
    - compute_chain_totals() uses:
        Ex_in_sys  = stage[0].computed['Ex_in_total']
        Ex_out_sys = last_stage.computed['Ex_out_total']
      So last stage outputs MUST NOT be empty.

    Rules:
    - stage.inputs / outputs / losses: only Joule (J) energy terms.
    - Tb_K is required for any term whose key contains "heat".
    """

    # ------------------------------------------------------------------
    # Minimal physical placeholder: assume 50% overall conversion
    # Electricity required to deliver the functional heat:
    # E_el_in ≈ Q_delivered / 0.5
    # ------------------------------------------------------------------
    electricity_in_J = assumption_value(
        value=float(heat_delivered_J.value) / 0.5,
        unit="J",
        meta={"note": "Phase7 minimal demo: assume 50% overall conversion from electricity to delivered heat"},
    )

    # ------------------------------------------------------------------
    # Stage 1: CONVERT (Electricity -> Heat)
    # Provide heat as OUTPUT so Ex_out_total is computed.
    # Tb_K must be provided because outputs contain 'heat_out'.
    # ------------------------------------------------------------------
    s1 = Stage(
        name="CONVERT_minimal",
        stage_type=StageType.CONVERT,
        inputs={
            "electricity_in": electricity_in_J,
        },
        outputs={
            "heat_out": heat_delivered_J,
        },
        losses={},
        Tb_K=Tb_K,
        computed={},
    )

    # ------------------------------------------------------------------
    # Stage 2: DELIVER (Heat delivered at boundary temperature Tb_K)
    # Provide heat both as input and output (delivery stage does not "destroy" heat energy).
    # This ensures:
    # - E_balance = 0
    # - Ex_out_total is computed from outputs (NOT zero)
    # ------------------------------------------------------------------
    s2 = Stage(
        name="DELIVER_minimal",
        stage_type=StageType.DELIVER,
        inputs={
            "heat_in": heat_delivered_J,
        },
        outputs={
            "heat_out": heat_delivered_J,
        },
        losses={},
        Tb_K=Tb_K,
        computed={},
    )

    chain = StageChain(stages=[s1, s2])
    chain.validate()
    return chain
