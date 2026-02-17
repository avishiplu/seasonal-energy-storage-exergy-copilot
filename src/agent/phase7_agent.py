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
from src.retrieval.missing_report import InfoStatus

from src.rag import build_index as rag_build_index

from src.simulation.build_stage_chain_minimal import build_minimal_stage_chain
from src.simulation.compute_stage import compute_stage
from src.simulation.compute_chain_totals import compute_chain_totals


# ============================================================
# CONFIG
# ============================================================

@dataclass
class AgentConfig:
    raw_papers_dir: Path = Path("data/raw_papers")
    state_path: Path = Path("data/cache/phase7_agent_state.json")
    functional_unit_heat_J: float = 1.0e6
    Tb_K: float = 353.15


# ============================================================
# UTIL
# ============================================================

def _snapshot_pdfs(pdf_dir: Path) -> str:
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


def _rebuild_index():
    rag_build_index.main()


def _make_component_plan(system_name: str) -> List[ComponentType]:
    s = (system_name or "").lower()
    if "mh" in s:
        return [
            ComponentType.ELECTROLYZER,
            ComponentType.METAL_HYDRIDE,
            ComponentType.FUEL_CELL,
            ComponentType.HEAT_PUMP,
            ComponentType.DISTRICT_HEAT,
        ]
    if "ptes" in s:
        return [
            ComponentType.HEAT_PUMP,
            ComponentType.DISTRICT_HEAT,
        ]
    return [ComponentType.ELECTROLYZER, ComponentType.DISTRICT_HEAT]


# ============================================================
# CORE UI-FRIENDLY AGENT STEP
# ============================================================

def run_phase7_step(
    system_name: str,
    scenario: Scenario,
    state: dict,
    pdf_dir: str,
    cfg: Optional[AgentConfig] = None,
) -> dict:

    cfg = cfg or AgentConfig()
    cfg.raw_papers_dir = Path(pdf_dir)

    # --------------------------------------------------------
    # 1. Detect PDF change
    # --------------------------------------------------------

    old_digest = state.get("pdf_digest")
    new_digest = _snapshot_pdfs(cfg.raw_papers_dir)

    if new_digest != old_digest:
        _rebuild_index()
        state["pdf_digest"] = new_digest
        _save_state(cfg.state_path, state)

    # --------------------------------------------------------
    # 2. Retrieval (Phase 6)
    # --------------------------------------------------------

    plan = _make_component_plan(system_name)
    retriever = Sprint2RetrieverAdapter()

    missing_all = []
    reliability = {"VALID": 0, "AMBIGUOUS": 0, "CONFLICT": 0}

    for comp in plan:
        qty_targets = [ri.key for ri in required_inputs_for(comp)]

        out = run_phase6_for_component(
            retriever=retriever,
            component=comp,
            component_label=comp.value.lower(),
            quantity_targets=qty_targets,
            allowed_variables=set(),
        )

        eqs = out["equations"]
        report = out["report"]

        for e in eqs:
            tag = getattr(e, "tag", "UNKNOWN")
            reliability[tag] = reliability.get(tag, 0) + 1

        for item in report.sorted_items():
            if item.status in {
                InfoStatus.MISSING,
                InfoStatus.AMBIGUOUS,
                InfoStatus.PARTIAL,
                InfoStatus.CONFLICT,
            }:
                missing_all.append(
                    {
                        "component": comp.value,
                        "key": item.key,
                        "unit": item.unit,
                        "critical": item.critical,
                        "status": item.status.value,
                        "citation_pdf": item.citation_pdf,
                        "citation_page": item.citation_page,
                    }
                )

    # --------------------------------------------------------
    # 3. Remove already provided assumptions
    # --------------------------------------------------------

    provided = set((state.get("assumptions") or {}).keys())
    missing_filtered = [m for m in missing_all if m["key"] not in provided]

    if missing_filtered:
        return {
            "status": "NEED_INPUT",
            "missing": missing_filtered,
            "results": None,
            "stages": None,
            "assumptions_used": list(provided),
            "reliability": reliability,
        }

    # --------------------------------------------------------
    # 4. Deterministic compute
    # --------------------------------------------------------

    heat_delivered = assumption_value(
        value=float(cfg.functional_unit_heat_J),
        unit="J",
        meta={"note": "Phase7 demo heat"},
    )

    Tb_K = assumption_value(
        value=float(cfg.Tb_K),
        unit="K",
        meta={"note": "Phase7 demo Tb"},
    )

    chain = build_minimal_stage_chain(heat_delivered_J=heat_delivered, Tb_K=Tb_K)
    chain.stages = [compute_stage(s, scenario=scenario) for s in chain.stages]
    chain = compute_chain_totals(chain)

    stages = []
    for s in chain.stages:
        stages.append(
            {
                "name": s.name,
                "ex_in": getattr(s.computed.get("Ex_in_total"), "value", None),
                "ex_out": getattr(s.computed.get("Ex_out_total"), "value", None),
                "ex_dest": getattr(s.computed.get("Ex_dest"), "value", None),
            }
        )

    return {
        "status": "DONE",
        "missing": [],
        "results": {
            "system_exergy_efficiency": None
            if chain.system_exergy_efficiency is None
            else chain.system_exergy_efficiency.value,
            "total_exergy_destruction_J": None
            if chain.total_exergy_destruction is None
            else chain.total_exergy_destruction.value,
        },
        "stages": stages,
        "assumptions_used": list(provided),
        "reliability": reliability,
    }
