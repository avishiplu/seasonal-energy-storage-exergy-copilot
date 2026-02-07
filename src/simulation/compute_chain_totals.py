# src/simulation/compute_chain_totals.py

from __future__ import annotations

from typing import Dict, Optional

from src.simulation.stage_chain import StageChain
from src.core.refusal import RefusalError
from src.core.values import computed_value, ValueSpec
from src.core.validate_values import require_source


def _require_J(v: ValueSpec, name: str) -> None:
    require_source(v)
    if v.unit != "J":
        raise RefusalError(
            code="REFUSE_CHAIN_TERM_UNIT_NOT_J",
            user_message=f"Cannot compute chain totals because {name} is not in Joule (J).",
            why="Chain roll-up requires all exergy and loss terms in Joule.",
            missing=[f"{name}.unit=J"],
            details={"got_unit": v.unit},
        )


def _sum_J(a: Optional[ValueSpec], b: ValueSpec, label: str) -> ValueSpec:
    _require_J(b, label)
    b_val = float(b.value)

    if a is None:
        return computed_value(
            value=b_val,
            unit="J",
            tool_name="compute_chain_totals",
            meta={"rollup": True, "init_from": label},
        )

    _require_J(a, label)
    a_val = float(a.value)

    return computed_value(
        value=a_val + b_val,
        unit="J",
        tool_name="compute_chain_totals",
        meta={"rollup": True, "sum_with": label},
    )


def compute_chain_totals(chain: StageChain) -> StageChain:
    """
    TASK 4.5 — Compute system totals (chain roll-up)
    """

    chain.validate()

    # 1) Roll up total losses
    totals_losses: Dict[str, ValueSpec] = {}

    for i, stage in enumerate(chain.stages, start=1):
        for loss_key, loss_v in (stage.losses or {}).items():
            label = f"stage[{i}].losses['{loss_key}']"
            current = totals_losses.get(loss_key)
            totals_losses[loss_key] = _sum_J(current, loss_v, label)

    chain.total_losses = totals_losses

    # 2) Roll up exergy destruction
    ex_dest_keys = ["Ex_dest", "Ex_destr", "Exergy_destruction"]
    total_ex_dest: Optional[ValueSpec] = None
    found_any = False

    for i, stage in enumerate(chain.stages, start=1):
        computed = stage.computed or {}

        v = None
        used_key = None
        for k in ex_dest_keys:
            if k in computed:
                v = computed[k]
                used_key = k
                break

        if v is None:
            continue

        found_any = True
        label = f"stage[{i}].computed['{used_key}']"
        total_ex_dest = _sum_J(total_ex_dest, v, label)

    if not found_any:
        raise RefusalError(
            code="REFUSE_CHAIN_EX_DEST_MISSING",
            user_message="Cannot compute chain exergy destruction because no stage provides Ex_dest.",
            why="At least one stage must compute exergy destruction for chain roll-up.",
            missing=[f"stage[i].computed one of {ex_dest_keys}"],
        )

    chain.total_exergy_destruction = total_ex_dest

    return chain
