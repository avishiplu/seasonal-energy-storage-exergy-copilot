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
    Minimal, physics-valid StageChain.

    RULES (important):
    - stage.inputs MUST contain only energy terms in Joule (J)
    - control / logic signals MUST NOT be stage inputs
    - all ASSUMPTION ValueSpec must include meta['note']
    """

    # Electricity input placeholder (ASSUMPTION, unit = J)
    electricity_in_J = assumption_value(
        value=float(heat_delivered_J.value),
        unit="J",
        meta={
            "note": "Skeleton placeholder: electricity_in_J equals delivered heat (temporary assumption)",
        },
    )

    # Stage 1: CONVERT (electricity → useful heat)
    s1 = Stage(
        name="CONVERT_minimal",
        stage_type=StageType.CONVERT,
        inputs={
            "electricity_in": electricity_in_J,
        },
        outputs={},
        losses={},
        Tb_K=None,
    )

    # Stage 2: DELIVER (heat delivery at boundary temperature)
    s2 = Stage(
        name="DELIVER_minimal",
        stage_type=StageType.DELIVER,
        inputs={
            "heat_in": heat_delivered_J,
        },
        outputs={},
        losses={},
        Tb_K=Tb_K,
    )

    chain = StageChain(stages=[s1, s2])
    chain.validate()
    return chain
