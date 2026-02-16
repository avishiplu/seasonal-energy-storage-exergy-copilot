# scripts/run_phase7_agent.py
from __future__ import annotations

from src.core.values import assumption_value
from src.core.scenario import Scenario
from src.agent.phase7_agent import run_phase7_agent


def main() -> None:
    # Minimal Scenario (T0 mandatory)
    scenario = Scenario(
        name="phase7_demo",
        location="Hamburg",
        time_start="2022-01-01",
        time_end="2022-01-02",
        T0_K=assumption_value(
            value=293.15,
            unit="K",
            meta={"note": "Phase7 demo: reference environment temperature"},
        ),
        Ts_K=assumption_value(
            value=353.15,
            unit="K",
            meta={"note": "Phase7 demo: supply temperature placeholder"},
        ),
        Tr_K=assumption_value(
            value=333.15,
            unit="K",
            meta={"note": "Phase7 demo: return temperature placeholder"},
        ),
        analysis_intent="teaching",
    )
    scenario.validate()

    system_name = "MH seasonal storage to DH"
    run_phase7_agent(system_name=system_name, scenario=scenario)


if __name__ == "__main__":
    main()
