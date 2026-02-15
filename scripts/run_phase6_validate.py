from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

from src.retrieval.component import ComponentType
from src.retrieval.sprint2_retriever_adapter import Sprint2RetrieverAdapter
from src.retrieval.phase6_runner import run_phase6_for_component
from src.retrieval.required_inputs import required_inputs_for



def main() -> None:
    retriever = Sprint2RetrieverAdapter()

    plan = [
        (ComponentType.ELECTROLYZER, "electrolyzer"),
        (ComponentType.METAL_HYDRIDE, "metal hydride"),
        (ComponentType.FUEL_CELL, "fuel cell"),
        (ComponentType.HEAT_PUMP, "heat pump"),
        (ComponentType.DISTRICT_HEAT, "district heating"),
    ]

    for comp, label in plan:
        quantity_targets = [ri.key for ri in required_inputs_for(comp)]

        out = run_phase6_for_component(
            retriever=retriever,
            component=comp,
            component_label=label,
            quantity_targets=quantity_targets,
            allowed_variables=set(),
        )

        print(f"\n================= COMPONENT: {comp.value} =================")
        print("\n================= EQUATIONS (first 20) =================")
        for e in out["equations"][:20]:
            print(f"- [{e.tag}] {e.canonical}")

        report = out["report"]
        print("\n================= MISSING REPORT =================")
        for item in report.sorted_items():
            print(
                f"{item.key:15s}  {item.status.value:10s}  "
                f"critical={item.critical}  unit={item.unit}  "
                f"cite={item.citation_pdf}:{item.citation_page}"
            )




if __name__ == "__main__":
    main()
