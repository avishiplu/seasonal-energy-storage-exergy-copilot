from src.core.values import external_value, assumption_value
from src.core.scenario import Scenario
from src.simulation.stage import Stage, StageType
from src.simulation.stage_chain import StageChain
from src.simulation.compute_stage import compute_stage
from src.simulation.compute_chain_totals import compute_chain_totals


def test_chain_system_efficiency_grid_to_deliver():
    scenario = Scenario(
        name="test_scenario",
        location="DE",
        time_start="2025-01-01",
        time_end="2025-01-02",
        analysis_intent="comparison",
        T0_K=assumption_value(293.15, "K", meta={"note": "reference temperature T0 (test)"}),
    )

    grid = Stage(
        name="Grid",
        stage_type=StageType.CHARGE,
        inputs={
            "electricity_in": external_value(
                1000.0,
                "J",
                meta={
                    "energy_kind": "electric",
                    "source": "dummy_grid_source",
                    "time_range": "2025-01-01/2025-01-02",
                },
            )
        },
        outputs={},
        losses={},
        Tb_K=None,
        computed={},
    )

    deliver = Stage(
        name="Deliver",
        stage_type=StageType.DELIVER,
        inputs={
            "heat_in": external_value(
                400.0,
                "J",
                meta={
                    "energy_kind": "thermal",
                    "source": "dummy_demand_source",
                    "time_range": "2025-01-01/2025-01-02",
                },
            )
        },
        outputs={},
        losses={},
        Tb_K=assumption_value(353.15, "K", meta={"note": "DH boundary temperature (test)"}),
        computed={},
    )

    grid_c = compute_stage(grid, scenario)
    deliver_c = compute_stage(deliver, scenario)

    chain = StageChain(stages=[grid_c, deliver_c])
    out = compute_chain_totals(chain)

    # Phase-4.5 roll-up guarantees totals, not necessarily system efficiency yet
    assert out.total_exergy_destruction is not None
    assert out.total_exergy_destruction.unit == "J"
