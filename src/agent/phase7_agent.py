# src/agent/phase7_agent.py
from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from src.core.values import ValueSpec, assumption_value
from src.core.scenario import Scenario
from src.core.refusal import RefusalError

from src.retrieval.component import ComponentType
from src.retrieval.required_inputs import required_inputs_for
from src.retrieval.sprint2_retriever_adapter import Sprint2RetrieverAdapter
from src.retrieval.phase6_runner import run_phase6_for_component
from src.retrieval.missing_report import MissingInformationReport, InfoStatus

from src.rag import build_index as rag_build_index

from src.simulation.build_stage_chain_minimal import build_minimal_stage_chain
from src.simulation.compute_stage import compute_stage
from src.simulation.compute_chain_totals import compute_chain_totals


@dataclass
class AgentConfig:
    raw_papers_dir: Path = Path("data/raw_papers")
    docs_dir: Path = Path("docs")
    state_path: Path = Path("data/cache/phase7_agent_state.json")

    # minimal demo compute placeholders (still valid end-to-end loop)
    functional_unit_heat_J: float = 1.0e6
    Tb_K: float = 353.15


def _snapshot_pdfs(pdf_dir: Path) -> str:
    """
    Detect new PDFs by hashing (filename + mtime + size).
    Returns a digest string.
    """
    pdf_dir = Path(pdf_dir)
    pdfs = sorted([p for p in pdf_dir.glob("*.pdf") if p.is_file()])
    parts: List[str] = []
    for p in pdfs:
        st = p.stat()
        parts.append(f"{p.name}|{int(st.st_mtime)}|{st.st_size}")
    blob = "\n".join(parts).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _rebuild_index() -> None:
    # Uses existing RAG index builder
    rag_build_index.main()


def _make_component_plan(system_name: str) -> List[ComponentType]:
    s = (system_name or "").lower()
    if "mh" in s or "metal" in s or "hydride" in s:
        return [
            ComponentType.ELECTROLYZER,
            ComponentType.METAL_HYDRIDE,
            ComponentType.FUEL_CELL,
            ComponentType.HEAT_PUMP,
            ComponentType.DISTRICT_HEAT,
        ]
    if "ptes" in s or "thermal" in s:
        return [
            ComponentType.HEAT_PUMP,
            ComponentType.DISTRICT_HEAT,
        ]
    return [ComponentType.ELECTROLYZER, ComponentType.DISTRICT_HEAT]


def _questions_from_missing(report: MissingInformationReport) -> List[dict]:
    """
    Return structured questions:
    {key, unit, critical, status}
    """
    qs: List[dict] = []
    for item in report.sorted_items():
        if item.status in {InfoStatus.MISSING, InfoStatus.PARTIAL, InfoStatus.AMBIGUOUS, InfoStatus.CONFLICT}:
            qs.append(
                {
                    "key": item.key,
                    "unit": item.unit,
                    "critical": item.critical,
                    "status": item.status.value,
                }
            )
    return qs


def _parse_user_value(key: str, expected_unit: str, raw: str) -> ValueSpec:
    """
    Store user input as ASSUMPTION ValueSpec.
    Accept:
    - "0.72"
    - "353.15 K"
    - "60 C"
    """
    s = (raw or "").strip().replace(",", ".")
    if not s:
        raise ValueError("Empty input")

    toks = s.split()
    if len(toks) == 1:
        val = float(toks[0])
        unit = expected_unit
    else:
        val = float(toks[0])
        unit = toks[1]

    return assumption_value(
        value=val,
        unit=unit,
        meta={"note": f"user assumption for {key}", "expected_unit": expected_unit},
    )


def _print_component_summary(comp: ComponentType, out: dict) -> None:
    eqs = out.get("equations", [])
    report: MissingInformationReport = out["report"]

    print(f"\n================= COMPONENT: {comp.value} =================")

    print("\nEQUATIONS (first 10):")
    for e in eqs[:10]:
        # show tag + canonical string
        print(f"- [{e.tag}] {e.canonical}")

    print("\nMISSING REPORT:")
    for item in report.sorted_items():
        cite = f"{item.citation_pdf}:{item.citation_page}" if item.citation_pdf else "None"
        print(
            f"- {item.key:15s} status={item.status.value:10s} "
            f"critical={item.critical} unit={item.unit} cite={cite}"
        )


def _run_minimal_compute(cfg: AgentConfig, scenario: Scenario) -> dict:
    """
    Minimal deterministic compute (proves Phase 7 loop end-to-end).
    Later you replace this with real MH/PTES StageChain builder.
    """
    heat_delivered = assumption_value(
        value=float(cfg.functional_unit_heat_J),
        unit="J",
        meta={"note": "Phase7 demo: fixed delivered heat (assumption)"},
    )
    Tb_K = assumption_value(
        value=float(cfg.Tb_K),
        unit="K",
        meta={"note": "Phase7 demo: boundary Tb (assumption)"},
    )

    chain = build_minimal_stage_chain(heat_delivered_J=heat_delivered, Tb_K=Tb_K)
    chain.stages = [compute_stage(s, scenario=scenario) for s in chain.stages]
    chain = compute_chain_totals(chain)

    return {
        "system_exergy_efficiency": None if chain.system_exergy_efficiency is None else chain.system_exergy_efficiency.value,
        "total_exergy_destruction_J": None if chain.total_exergy_destruction is None else chain.total_exergy_destruction.value,
    }


def run_phase7_agent(system_name: str, scenario: Scenario, cfg: Optional[AgentConfig] = None) -> None:
    """
    Phase 7 end-to-end loop:
    - detect new PDFs -> rebuild index
    - run Phase 6 retrieval -> missing report
    - ask specific questions -> store as assumptions
    - run deterministic compute
    - print results + assumptions
    """
    cfg = cfg or AgentConfig()

    # 7.1.0 require the system structuring doc exists
    required_doc = cfg.docs_dir / "add_new_storage_system.md"
    if not required_doc.exists():
        raise RefusalError(
            code="REFUSE_PHASE7_DOC_MISSING",
            user_message="docs/add_new_storage_system.md is missing, cannot start Phase 7 agent.",
            why="Agent must follow the mandatory system-structuring process before building stage chains.",
            missing=["docs/add_new_storage_system.md"],
        )

    state = _load_state(cfg.state_path)
    old_digest = state.get("pdf_digest")

    new_digest = _snapshot_pdfs(cfg.raw_papers_dir)
    if new_digest != old_digest:
        print("New/changed PDFs detected -> rebuilding index ...")
        _rebuild_index()
        state["pdf_digest"] = new_digest
        _save_state(cfg.state_path, state)

    plan = _make_component_plan(system_name)
    retriever = Sprint2RetrieverAdapter()

    user_assumptions: Dict[str, ValueSpec] = {}

    for comp in plan:
        qty_targets = [ri.key for ri in required_inputs_for(comp)]

        out = run_phase6_for_component(
            retriever=retriever,
            component=comp,
            component_label=comp.value.replace("_", " ").lower(),
            quantity_targets=qty_targets,
            allowed_variables=set(),
        )

        _print_component_summary(comp, out)

        report: MissingInformationReport = out["report"]
        questions = _questions_from_missing(report)

        for q in questions:
            key = q["key"]
            unit = q["unit"]
            print(f"\nQUESTION: Provide '{key}' in unit '{unit}'.")
            ans = input("Type value (or 'skip', or 'pdf' after adding new PDFs): ").strip()

            if ans.lower() == "skip":
                continue

            if ans.lower() == "pdf":
                # re-check PDFs and rebuild index if changed
                digest2 = _snapshot_pdfs(cfg.raw_papers_dir)
                if digest2 != state.get("pdf_digest"):
                    print("PDF changed -> rebuilding index ...")
                    _rebuild_index()
                    state["pdf_digest"] = digest2
                    _save_state(cfg.state_path, state)
                # re-run retrieval for this component
                out = run_phase6_for_component(
                    retriever=retriever,
                    component=comp,
                    component_label=comp.value.replace("_", " ").lower(),
                    quantity_targets=qty_targets,
                    allowed_variables=set(),
                )
                _print_component_summary(comp, out)
                continue

            try:
                user_assumptions[key] = _parse_user_value(key, unit, ans)
            except Exception as e:
                print("Could not store answer:", e)

    print("\nRunning deterministic compute (minimal demo)...")
    try:
        result = _run_minimal_compute(cfg, scenario)
    except RefusalError as e:
        print("\nREFUSAL:", e.user_message)
        print("WHY:", e.why)
        print("MISSING:", e.missing)
        return

    print("\n================= FINAL RESULTS =================")
    print("system_exergy_efficiency:", result["system_exergy_efficiency"])
    print("total_exergy_destruction_J:", result["total_exergy_destruction_J"])

    print("\n================= ASSUMPTIONS (User Answers) =================")
    if not user_assumptions:
        print("(none)")
    else:
        for k, v in user_assumptions.items():
            print(f"- {k}: {v.value} {v.unit} (source={v.source_type.value})")
