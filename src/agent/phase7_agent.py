# src/agent/phase7_agent.py
from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from src.core.values import assumption_value
from src.core.scenario import Scenario

from src.retrieval.component import ComponentType
from src.retrieval.required_inputs import required_inputs_for
from src.retrieval.sprint2_retriever_adapter import Sprint2RetrieverAdapter
from src.retrieval.phase6_runner import run_phase6_for_component

from src.rag import build_index as rag_build_index

from src.simulation.build_stage_chain_minimal import build_minimal_stage_chain
from src.simulation.build_stage_chain_ptes import build_stage_chain_ptes
from src.simulation.compute_stage import compute_stage
from src.simulation.compute_chain_totals import compute_chain_totals


# ============================================================
# CONFIG
# ============================================================

@dataclass
class AgentConfig:
    raw_papers_dir: Path = Path("data/raw_papers")
    state_path: Path = Path("data/cache/phase7_agent_state.json")
    functional_unit_heat_J: float = 1.0e6  # demo functional unit (J)
    Tb_K: float = 353.15                   # fallback DH boundary temperature (K)


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


def _save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _rebuild_index() -> None:
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
            ComponentType.PTES,
            ComponentType.DISTRICT_HEAT,
        ]

    # default fallback
    return [ComponentType.ELECTROLYZER, ComponentType.DISTRICT_HEAT]


def _to_float_assumption(assumptions: dict, key: str, unit: str):
    """
    Convert a saved assumption dict to ValueSpec with a fixed unit.
    (We intentionally do NOT guess values.)
    """
    return assumption_value(
        value=float(assumptions[key]["value"]),
        unit=unit,
        meta={"note": f"{key} from user assumptions"},
    )


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
    # 1) Detect PDF change → rebuild index if needed
    # --------------------------------------------------------
    old_digest = state.get("pdf_digest")
    new_digest = _snapshot_pdfs(cfg.raw_papers_dir)

    if new_digest != old_digest:
        _rebuild_index()
        state["pdf_digest"] = new_digest
        _save_state(cfg.state_path, state)

    # --------------------------------------------------------
    # 2) Retrieval (Phase 6) → build missing list
    # ROOT RULE:
    #   Missing means: user has NOT provided numeric value in assumptions,
    #   even if evidence is FOUND in PDFs.
    # --------------------------------------------------------
    plan = _make_component_plan(system_name)
    retriever = Sprint2RetrieverAdapter()

    assumptions = state.get("assumptions") or {}
    provided = set(assumptions.keys())

    missing_all: list[dict] = []
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
            if item.key in provided:
                continue
            missing_all.append(
                {
                    "component": comp.value,
                    "key": item.key,
                    "unit": item.unit,
                    "critical": item.critical,
                    "status": item.status.value,       # keep evidence label
                    "citation_pdf": item.citation_pdf,
                    "citation_page": item.citation_page,
                }
            )

    if missing_all:
        return {
            "status": "NEED_INPUT",
            "missing": missing_all,
            "results": None,
            "stages": None,
            "assumptions_used": list(provided),
            "reliability": reliability,
        }

    # --------------------------------------------------------
    # 3) Deterministic compute
    # --------------------------------------------------------
    # Functional unit heat delivered
    heat_delivered = assumption_value(
        value=float(cfg.functional_unit_heat_J),
        unit="J",
        meta={"note": "Phase7 functional unit heat (demo)"},
    )

    # Tb_K: prefer user assumption; else fallback to config
    if "Tb_K" in assumptions:
        Tb_K = _to_float_assumption(assumptions, "Tb_K", "K")
    else:
        Tb_K = assumption_value(
            value=float(cfg.Tb_K),
            unit="K",
            meta={"note": "Tb_K fallback from AgentConfig"},
        )

    # System switch
    if "ptes" in (system_name or "").lower():

        # PTES REAL INPUTS (must exist in assumptions; never guessed)
        required_keys = [
            "eta_collector", "A_collector_m2", "G_solar_Wm2", "t_operation_s",
            "UA_WK", "T_store_K", "t_storage_s",
            "COP", "Tb_K",
        ]
        missing_keys = [k for k in required_keys if k not in assumptions]

        if missing_keys:
            # This should not usually happen because retrieval step already built missing_all,
            # but we keep a hard guard to prevent crashes.
            return {
                "status": "NEED_INPUT",
                "missing": [
                    {
                        "component": "PTES",
                        "key": k,
                        "unit": "?",
                        "critical": True,
                        "status": "MISSING",
                        "citation_pdf": None,
                        "citation_page": None,
                    }
                    for k in missing_keys
                ],
                "results": None,
                "stages": None,
                "assumptions_used": list(provided),
                "reliability": reliability,
            }

        eta_collector = _to_float_assumption(assumptions, "eta_collector", "1")
        A_collector_m2 = _to_float_assumption(assumptions, "A_collector_m2", "m2")
        G_solar_Wm2 = _to_float_assumption(assumptions, "G_solar_Wm2", "W/m2")
        t_operation_s = _to_float_assumption(assumptions, "t_operation_s", "s")

        UA_WK = _to_float_assumption(assumptions, "UA_WK", "W/K")
        T_store_K = _to_float_assumption(assumptions, "T_store_K", "K")
        t_storage_s = _to_float_assumption(assumptions, "t_storage_s", "s")

        COP = _to_float_assumption(assumptions, "COP", "1")

        # Use Tb_K from assumptions for delivered heat boundary
        Tb_DH_K = Tb_K

        # T0_K from Scenario UI (not guessed)
        T0_K = assumption_value(
            value=float(scenario.T0_K.value),
            unit="K",
            meta={"note": "T0 from Scenario UI"},
        )

        try:
            chain = build_stage_chain_ptes(
                Q_delivered_J=heat_delivered,
                Tb_DH_K=Tb_DH_K,
                T_store_K=T_store_K,
                T0_K=T0_K,
                eta_collector=eta_collector,
                A_collector_m2=A_collector_m2,
                G_solar_Wm2=G_solar_Wm2,
                t_operation_s=t_operation_s,
                UA_WK=UA_WK,
                t_storage_s=t_storage_s,
                COP=COP,
            )
        except ValueError as e:
            return {
                "status": "NEED_INPUT",
                "missing": [
                    {
                        "component": "PTES",
                        "key": "PTES_FEASIBILITY",
                        "unit": "-",
                        "critical": True,
                        "status": "INFEASIBLE",
                        "citation_pdf": None,
                        "citation_page": None,
                    }
                ],
                "results": {"message": str(e)},
                "stages": None,
                "assumptions_used": list(provided),
                "reliability": reliability,
            }

    else:
        chain = build_minimal_stage_chain(heat_delivered_J=heat_delivered, Tb_K=Tb_K)

    # Compute per-stage exergy and totals
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
