from __future__ import annotations

from typing import Dict, Optional

from src.simulation.stage_chain import StageChain
from src.core.refusal import RefusalError
from src.core.values import ValueSpec, computed_value
from src.core.validate_values import require_source

from src.tools.exergy_efficiency import exergy_efficiency


def _require_J(v: ValueSpec, name: str) -> None:
    """
    Enforce Joule-only rollups for chain totals.
    This prevents unit-mixing bugs in reproducible totals.
    """
    require_source(v)
    if v.unit != "J":
        raise RefusalError(
            code="REFUSE_CHAIN_TERM_UNIT_NOT_J",
            user_message=f"Cannot compute chain totals because {name} is not in Joule (J).",
            why="Chain roll-up requires all energy/exergy terms to be in Joule (J).",
            missing=[f"{name}.unit=J"],
            details={"got_unit": v.unit},
        )


def _sum_J(acc: Optional[ValueSpec], v: ValueSpec, label: str) -> ValueSpec:
    """
    Deterministically sum Joule terms into a computed ValueSpec.
    """
    _require_J(v, label)
    v_val = float(v.value)

    if acc is None:
        return computed_value(
            value=v_val,
            unit="J",
            tool_name="compute_chain_totals",
            meta={"rollup": True, "init_from": label},
        )

    _require_J(acc, "accumulator")
    acc_val = float(acc.value)

    return computed_value(
        value=acc_val + v_val,
        unit="J",
        tool_name="compute_chain_totals",
        meta={"rollup": True, "sum_with": label},
    )


def _get_computed(stage, key: str) -> Optional[ValueSpec]:
    """
    Safe getter for stage.computed values.
    """
    comp = stage.computed or {}
    return comp.get(key)


def compute_chain_totals(chain: StageChain) -> StageChain:
    """
    TASK 4.5 — Compute system totals (chain roll-up)

    PURPOSE (বাংলায়):
    - Phase 4-এর লক্ষ্য হলো deterministic হিসাব: stage থেকে totals-এ উঠানো (roll-up)।
    - এই ফাংশন system-level reproducible totals তৈরি করে:
      (a) total energy losses
      (b) total exergy destruction
      (c) system exergy efficiency (grid → delivered)

    MAIN BLOCKS (বাংলায়):
    1) Validation: chain/stages ফাঁকা হলে refuse
    2) Loss roll-up: stage.losses dict থেকে key-wise total_losses তৈরি
    3) Exergy destruction roll-up: stage.computed['Ex_dest'] যোগ করে total_exergy_destruction তৈরি
    4) System efficiency: Ex_out / Ex_in (deterministic tool) → chain.system_exergy_efficiency

    INTENTIONALLY NOT DONE (বাংলায়):
    - কোনো stage input/output guess করা হয় না
    - কোনো agent logic / PDF extraction এখানে নেই
    - stage-level physics এখানে implement করা নেই (ওটা tools + compute_stage-এর কাজ)
    """

    # ----------------------------
    # 0) Validate chain
    # ----------------------------
    chain.validate()

    if not chain.stages:
        raise RefusalError(
            code="REFUSE_CHAIN_EMPTY",
            user_message="Cannot compute chain totals because StageChain has no stages.",
            why="Roll-up requires at least one stage.",
            missing=["chain.stages (non-empty)"],
        )

    # ----------------------------
    # 1) 4.5.1 Sum stage energy losses (key-wise)
    # ----------------------------
    totals_losses: Dict[str, ValueSpec] = {}

    for i, stage in enumerate(chain.stages):
        for loss_key, loss_v in (stage.losses or {}).items():
            label = f"stage[{i}].losses['{loss_key}']"
            totals_losses[loss_key] = _sum_J(totals_losses.get(loss_key), loss_v, label)

    chain.total_losses = totals_losses

    # ----------------------------
    # 2) 4.5.2 Sum stage exergy destruction
    # ----------------------------
    total_ex_dest: Optional[ValueSpec] = None
    found_any = False

    for i, stage in enumerate(chain.stages):
        exd = _get_computed(stage, "Ex_dest")
        if exd is None:
            continue

        found_any = True
        label = f"stage[{i}].computed['Ex_dest']"
        total_ex_dest = _sum_J(total_ex_dest, exd, label)

    if not found_any:
        raise RefusalError(
            code="REFUSE_CHAIN_EX_DEST_MISSING",
            user_message="Cannot compute chain exergy destruction because no stage provides Ex_dest.",
            why="At least one stage must compute Ex_dest for chain roll-up.",
            missing=["stage[i].computed['Ex_dest'] (at least one)"],
        )

    chain.total_exergy_destruction = total_ex_dest

    # ----------------------------
    # 3) 4.5.3 System exergy efficiency (grid → delivered)
    # ----------------------------
    # Boundary assumption for Phase 4 completion:
    # - Ex_in_system: first stage computed Ex_in_total (grid electricity boundary)
    # - Ex_out_system: last stage computed Ex_out_total (delivery boundary), fallback Ex_out (legacy key)

    first = chain.stages[0]
    Ex_in_sys = _get_computed(first, "Ex_in_total")
    if Ex_in_sys is None:
        raise RefusalError(
            code="REFUSE_CHAIN_SYSTEM_EX_IN_MISSING",
            user_message="Cannot compute system exergy efficiency because system Ex_in is missing.",
            why="System Ex_in is taken from the first stage computed Ex_in_total (grid electricity boundary).",
            missing=["stage[0].computed['Ex_in_total']"],
        )

    last = chain.stages[-1]
    Ex_out_sys = _get_computed(last, "Ex_out_total")
    if Ex_out_sys is None:
        # backward compatibility with older DELIVER implementation
        Ex_out_sys = _get_computed(last, "Ex_out")

    if Ex_out_sys is None:
        raise RefusalError(
            code="REFUSE_CHAIN_SYSTEM_EX_OUT_MISSING",
            user_message="Cannot compute system exergy efficiency because system Ex_out is missing.",
            why="System Ex_out is taken from the last stage (DELIVER) computed exergy output.",
            missing=["last_stage.computed['Ex_out_total'] or last_stage.computed['Ex_out']"],
        )

    eta_sys = exergy_efficiency(Ex_out=Ex_out_sys, Ex_in=Ex_in_sys)
    chain.system_exergy_efficiency = eta_sys

    return chain

