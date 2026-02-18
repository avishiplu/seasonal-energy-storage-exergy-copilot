from __future__ import annotations

from typing import Dict

from src.simulation.stage import Stage, StageType
from src.core.scenario import Scenario
from src.core.refusal import RefusalError
from src.core.values import ValueSpec, computed_value
from src.core.validate_values import require_source

from src.tools.exergy_core import thermal_exergy_of_heat
from src.tools.exergy_destruction_balance_full import exergy_destruction_balance_full


# ----------------------------
# Helper utilities (deterministic, no agent logic)
# ----------------------------

def _require_J(v: ValueSpec, label: str) -> None:
    require_source(v)
    if v.unit != "J":
        raise RefusalError(
            code="REFUSE_STAGE_TERM_UNIT_NOT_J",
            user_message=f"Cannot compute stage totals because {label} is not in Joule (J).",
            why="Stage energy/exergy bookkeeping requires all terms in Joule (J).",
            missing=[f"{label}.unit=J"],
            details={"got_unit": v.unit},
        )


def _is_heat_key(key: str) -> bool:
    """
    Heuristic: any key that contains 'heat' is treated as heat energy.
    Examples: heat_in, heat_out, heat_loss, waste_heat, etc.
    """
    return "heat" in key.lower()


def _sum_terms_J(terms: Dict[str, ValueSpec], label_prefix: str) -> ValueSpec:
    total = 0.0
    for k, v in (terms or {}).items():
        _require_J(v, f"{label_prefix}['{k}']")
        total += float(v.value)

    return computed_value(
        value=total,
        unit="J",
        tool_name="compute_stage",
        meta={"rollup": True, "kind": label_prefix},
    )


def _exergy_of_terms(
    terms: Dict[str, ValueSpec],
    label_prefix: str,
    Tb_K: ValueSpec | None,
    scenario: Scenario,
) -> ValueSpec:
    """
    Convert energy-like terms to exergy-like terms.

    Rules (deterministic, conservative):
    - If key looks like heat -> use thermal_exergy_of_heat(Q, Tb_K, T0_K)
      and refuse if Tb_K missing.
    - Otherwise assume electricity/work high-grade -> Ex = E (requires J).
    """
    total_ex = 0.0

    for k, v in (terms or {}).items():
        _require_J(v, f"{label_prefix}['{k}']")
        v_val = float(v.value)

        if _is_heat_key(k):
            if Tb_K is None:
                raise RefusalError(
                    code="REFUSE_STAGE_TB_MISSING_FOR_HEAT_TERM",
                    user_message="Cannot compute exergy because stage has heat terms but Tb_K is missing.",
                    why="Heat exergy requires a boundary temperature Tb_K.",
                    missing=["stage.Tb_K"],
                    details={"term_key": k, "location": label_prefix},
                )
            ex_v = thermal_exergy_of_heat(Q=v, Tb_K=Tb_K, T0_K=scenario.T0_K)
            total_ex += float(ex_v.value)
        else:
            # electricity/work-like term: Ex = E
            total_ex += v_val

    return computed_value(
        value=total_ex,
        unit="J",
        tool_name="compute_stage",
        meta={"rollup": True, "kind": f"exergy_from_{label_prefix}"},
    )


def compute_stage(stage: Stage, scenario: Scenario) -> Stage:
    """
    TASK 4.4 — Compute stage results
    - Energy totals: in/out/loss + balance
    - Exergy totals: in/out/loss
    - Exergy destruction (full balance): Ex_in + W_in - Ex_out - W_out - Ex_loss

    NOTE: This function is deterministic and refuses on missing/non-physical info.
    """

    computed = dict(stage.computed)

    # --------
    # 4.4.1 Energy bookkeeping
    # --------
    E_in_total = _sum_terms_J(stage.inputs, "stage.inputs")
    E_out_total = _sum_terms_J(stage.outputs, "stage.outputs")
    E_loss_total = _sum_terms_J(stage.losses, "stage.losses")

    E_balance = computed_value(
        value=float(E_in_total.value) - float(E_out_total.value) - float(E_loss_total.value),
        unit="J",
        tool_name="compute_stage",
        meta={"formula": "E_in_total - E_out_total - E_loss_total"},
    )

    computed["E_in_total"] = E_in_total
    computed["E_out_total"] = E_out_total
    computed["E_loss_total"] = E_loss_total
    computed["E_balance"] = E_balance

    # --------
    # 4.4.2 Exergy totals (heat exergy where applicable)
    # --------
    Ex_in_total = _exergy_of_terms(stage.inputs, "stage.inputs", stage.Tb_K, scenario)
    Ex_out_total = _exergy_of_terms(stage.outputs, "stage.outputs", stage.Tb_K, scenario)

    # Loss exergy: conservative rule
    Ex_loss_total = _exergy_of_terms(stage.losses, "stage.losses", stage.Tb_K, scenario)

    computed["Ex_in_total"] = Ex_in_total
    computed["Ex_out_total"] = Ex_out_total
    computed["Ex_loss_total"] = Ex_loss_total

    # Backward-compat convenience:
    # If this is a DELIVER stage and it has heat_in, keep Ex_out as well (older key).
    if stage.stage_type == StageType.DELIVER and "heat_in" in (stage.inputs or {}):
        if stage.Tb_K is None:
            raise RefusalError(
                code="REFUSE_STAGE_DELIVER_TB_MISSING",
                user_message="Cannot compute DELIVER exergy because Tb_K is missing.",
                why="Delivered heat exergy needs Tb_K at the delivery boundary.",
                missing=["stage.Tb_K"],
            )
        computed["Ex_out"] = thermal_exergy_of_heat(
            Q=stage.inputs["heat_in"],
            Tb_K=stage.Tb_K,
            T0_K=scenario.T0_K,
        )

    # --------
    # 4.4.3 Exergy destruction (second law)
    # --------
    try:
        Ex_dest = exergy_destruction_balance_full(
            Ex_in=Ex_in_total,
            Ex_out=Ex_out_total,
            W_in=None,
            W_out=None,
            Ex_loss=Ex_loss_total,
        )
    except RefusalError as e:
        # Re-raise with stage context so UI can show exactly where it failed.
        details = {}
        if hasattr(e, "details") and isinstance(e.details, dict):
            details.update(e.details)

        details.update(
            {
                "stage_name": stage.name,
                "stage_type": str(stage.stage_type),
                "Tb_K": None if stage.Tb_K is None else {"value": stage.Tb_K.value, "unit": stage.Tb_K.unit},
                "T0_K": {"value": scenario.T0_K.value, "unit": scenario.T0_K.unit},
                "Ex_in_total": {"value": Ex_in_total.value, "unit": Ex_in_total.unit},
                "Ex_out_total": {"value": Ex_out_total.value, "unit": Ex_out_total.unit},
                "Ex_loss_total": {"value": Ex_loss_total.value, "unit": Ex_loss_total.unit},
                "E_in_total": {"value": E_in_total.value, "unit": E_in_total.unit},
                "E_out_total": {"value": E_out_total.value, "unit": E_out_total.unit},
                "E_loss_total": {"value": E_loss_total.value, "unit": E_loss_total.unit},
                "E_balance": {"value": E_balance.value, "unit": E_balance.unit},
            }
        )

        raise RefusalError(
            code=getattr(e, "code", "REFUSE_STAGE_EXERGY_DEST"),
            user_message=getattr(e, "user_message", str(e)),
            why=getattr(e, "why", "Stage-level exergy destruction check failed."),
            missing=getattr(e, "missing", []),
            details=details,
        )

    computed["Ex_dest"] = Ex_dest


    # Return new frozen Stage
    return Stage(
        name=stage.name,
        stage_type=stage.stage_type,
        inputs=stage.inputs,
        outputs=stage.outputs,
        losses=stage.losses,
        Tb_K=stage.Tb_K,
        computed=computed,
    )
