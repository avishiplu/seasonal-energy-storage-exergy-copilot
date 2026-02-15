from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.cache.external_cache import init_cache
from src.ingestion.smard_prefill import smard_prefill_from_downloadcenter
from src.retrieval.external_inputs import (
    price_at_hour_external,
    ambient_temperature_at_hour_external,
)

from src.core.values import assumption_value
from src.core.scenario import Scenario

from src.simulation.build_stage_chain_minimal import build_minimal_stage_chain
from src.simulation.compute_stage import compute_stage
from src.simulation.compute_chain_totals import compute_chain_totals
from src.simulation.export_timeseries import rows_to_csv


# -----------------------------------------------------------------------------
# Time iterator (hourly, UTC)
# -----------------------------------------------------------------------------
def iter_hours(start_utc: datetime, end_utc: datetime):
    """
    Yield hourly timestamps [start_utc, end_utc) aligned to full hours in UTC.
    """
    t = start_utc.replace(minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    end_utc = end_utc.replace(minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    while t < end_utc:
        yield t
        t += timedelta(hours=1)


# -----------------------------------------------------------------------------
# Output row used for printing / legacy compatibility
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class HourRow:
    time_iso: str
    market: str
    price_eur_per_mwh: float
    electrolyzer_on: bool
    exergy_destruction_total: Optional[float]


# -----------------------------------------------------------------------------
# SMARD Download Center payload builder (scenario-driven window)
# -----------------------------------------------------------------------------
def _smard_payload_for_market(market: str, start_utc: datetime, end_utc: datetime) -> dict:
    """
    Build payload for the SMARD Download Center backend (nip-download-manager),
    using the scenario time window.

    NOTE:
    - This is external data ingestion only (Phase-5).
    - No physics is performed here.
    """
    ts_from_ms = int(start_utc.replace(tzinfo=timezone.utc).timestamp() * 1000)
    ts_to_ms = int(end_utc.replace(tzinfo=timezone.utc).timestamp() * 1000)

    return {
        "request_form": [
            {
                "format": "CSV",
                "moduleIds": [
                    8004169, 8004170, 8000251, 8005078,
                    8000252, 8000253, 8000254, 8000255,
                    8000256, 8000257, 8000258, 8000259,
                    8000260, 8000261, 8000262,
                    8004996, 8004997,
                ],
                "region": market,
                "timestamp_from": ts_from_ms,
                "timestamp_to": ts_to_ms,
                "type": "discrete",
                "language": "en",
                "resolution": "hour",
            }
        ]
    }


# -----------------------------------------------------------------------------
# Minimal scenario builder (must provide T0_K for exergy tools)
# -----------------------------------------------------------------------------
def _make_minimal_scenario(market: str, start_utc: datetime, end_utc: datetime) -> Scenario:
    """
    Build a minimal valid Scenario.
    - T0_K is mandatory for exergy of heat computations.
    - All assumption_value(...) must include meta['note'] (validator rule).
    """
    scenario = Scenario(
        name="phase5_skeleton",
        location=market,
        time_start=start_utc.date().isoformat(),
        time_end=end_utc.date().isoformat(),
        T0_K=assumption_value(
            value=293.15,
            unit="K",
            meta={"note": "Skeleton scenario: ambient reference temperature T0 for exergy"},
        ),
        Ts_K=assumption_value(
            value=353.15,
            unit="K",
            meta={"note": "Skeleton scenario: supply temperature Ts (placeholder)"},
        ),
        Tr_K=assumption_value(
            value=333.15,
            unit="K",
            meta={"note": "Skeleton scenario: return temperature Tr (placeholder)"},
        ),
        analysis_intent="teaching",
    )

    scenario.validate()
    return scenario


# -----------------------------------------------------------------------------
# Phase 5 runner:
# - Step A: external data prefill (price only here) + cache init
# - Step B: hourly loop reading cached EXTERNAL values (price + weather)
# - Step C: export Phase 5.5 time-series table to CSV
# -----------------------------------------------------------------------------
def run_hourly_minimal_exergy(
    start_utc: datetime,
    end_utc: datetime,
    market: str = "DE-LU",
) -> List[HourRow]:
    """
    Phase 5 flow:

    A) External inputs + cache:
       - init_cache()
       - prefill SMARD data into SQLite (skip if already cached)

    B) Hourly loop:
       - Read cached price (ValueSpec(EXTERNAL))
       - Read cached ambient temperature (ValueSpec(EXTERNAL))
       - Decide a control flag (outside physics, ASSUMPTION)
       - Maintain minimal storage state (ASSUMPTION only; no physics)
       - Build a minimal StageChain (stage.inputs energy terms must be Joule)
       - compute_stage(stage, scenario) for each stage
       - compute_chain_totals(chain)

    C) Phase 5.5 export:
       - Collect rows with:
         time, stage, variable, value, unit, source_type, source (+market as extra column)
       - Save CSV under data/cache/timeseries/
    """
    init_cache()

    # Prefill external SMARD prices for this scenario window (skip if already cached for market)
    payload = _smard_payload_for_market(market=market, start_utc=start_utc, end_utc=end_utc)
    prefill_res = smard_prefill_from_downloadcenter(payload)
    print("SMARD prefill:", prefill_res)

    scenario = _make_minimal_scenario(market=market, start_utc=start_utc, end_utc=end_utc)

    out: List[HourRow] = []
    rows: List[Dict[str, Any]] = []

    # Phase-5 storage placeholder state (ASSUMPTION ONLY)
    storage_level = 0.0

    for t in iter_hours(start_utc, end_utc):
        # 1) External price (cache-only, EXTERNAL)
        price_vs = price_at_hour_external(market=market, hour_utc=t)

        # 2) External ambient temperature (cache-only, EXTERNAL)
        # NOTE: external_inputs returns Kelvin already. No unit conversion here.
        T_amb_vs = ambient_temperature_at_hour_external(location="Hamburg", hour_utc=t)


        # 3) Control decision (ASSUMPTION, NOT physics)
        electrolyzer_on = float(price_vs.value) < 50.0
        control_vs = assumption_value(
            value=bool(electrolyzer_on),
            unit="-",
            meta={"note": "Electrolyzer ON when day-ahead price < 50 EUR/MWh", "time": t.isoformat()},
        )

        # 4) Storage state update (ASSUMPTION ONLY, explicit, no thermodynamics)
        if electrolyzer_on:
            storage_level += 1.0
        else:
            storage_level = max(storage_level - 0.5, 0.0)

        storage_vs = assumption_value(
            value=float(storage_level),
            unit="-",
            meta={"note": "Phase-5 placeholder storage state (no physics)", "time": t.isoformat()},
        )

        # 5) Skeleton physics inputs (ASSUMPTION)
        # NOTE: stage.inputs energy terms must be Joule ("J")
        heat_delivered_J = assumption_value(
            value=1.0e6,  # placeholder: 1 MJ delivered per hour
            unit="J",
            meta={"note": "Skeleton: fixed delivered heat per hour", "time": t.isoformat()},
        )

        Tb_K = assumption_value(
            value=353.15,  # placeholder delivery boundary temperature
            unit="K",
            meta={"note": "Skeleton: delivery boundary temperature Tb", "time": t.isoformat()},
        )

        # 6) Build minimal StageChain (physics-only composition)
        chain = build_minimal_stage_chain(heat_delivered_J=heat_delivered_J, Tb_K=Tb_K)

        # 7) Deterministic compute (NO inline math)
        chain.stages = [compute_stage(stage, scenario=scenario) for stage in chain.stages]
        chain = compute_chain_totals(chain)

        # 8) Extract key computed metric (optional)
        ex_dest_val: Optional[float] = None
        if getattr(chain, "total_exergy_destruction", None) is not None:
            try:
                ex_dest_val = float(chain.total_exergy_destruction.value)  # type: ignore[union-attr]
            except Exception:
                ex_dest_val = None

        # 9) Phase 5.5 time-series rows (required schema)
        # External inputs
        rows.append(
            {
                "time": t.isoformat(),
                "market": market,
                "stage": "EXTERNAL",
                "variable": "day_ahead_price",
                "value": float(price_vs.value),
                "unit": price_vs.unit,
                "source_type": price_vs.source_type.value,
                "source": "SMARD",
            }
        )
        rows.append(
            {
                "time": t.isoformat(),
                "market": market,
                "stage": "EXTERNAL",
                "variable": "ambient_temperature",
                "value": float(T_amb_vs.value),
                "unit": T_amb_vs.unit,
                "source_type": T_amb_vs.source_type.value,
                "source": "DWD",
            }
        )

        # Control + storage (ASSUMPTION)
        rows.append(
            {
                "time": t.isoformat(),
                "market": market,
                "stage": "CONTROL",
                "variable": "electrolyzer_on",
                "value": int(bool(control_vs.value)),  # CSV-safe 0/1
                "unit": control_vs.unit,
                "source_type": control_vs.source_type.value,
                "source": "rule: price < 50 EUR/MWh",
            }
        )
        rows.append(
            {
                "time": t.isoformat(),
                "market": market,
                "stage": "STORAGE",
                "variable": "storage_level",
                "value": float(storage_vs.value),
                "unit": storage_vs.unit,
                "source_type": storage_vs.source_type.value,
                "source": "explicit assumption",
            }
        )

        # Optional computed rows (if present)
        if getattr(chain, "total_exergy_destruction", None) is not None:
            vs = chain.total_exergy_destruction  # type: ignore[assignment]
            rows.append(
                {
                    "time": t.isoformat(),
                    "market": market,
                    "stage": "SYSTEM",
                    "variable": "total_exergy_destruction",
                    "value": float(vs.value),
                    "unit": vs.unit,
                    "source_type": vs.source_type.value,
                    "source": "compute_chain_totals",
                }
            )

        if getattr(chain, "system_exergy_efficiency", None) is not None:
            vs = chain.system_exergy_efficiency  # type: ignore[assignment]
            rows.append(
                {
                    "time": t.isoformat(),
                    "market": market,
                    "stage": "SYSTEM",
                    "variable": "system_exergy_efficiency",
                    "value": float(vs.value),
                    "unit": vs.unit,
                    "source_type": vs.source_type.value,
                    "source": "compute_chain_totals",
                }
            )

        if getattr(chain, "total_losses", None):
            for loss_key, vs in chain.total_losses.items():
                rows.append(
                    {
                        "time": t.isoformat(),
                        "market": market,
                        "stage": "SYSTEM",
                        "variable": f"loss_{loss_key}",
                        "value": float(vs.value),
                        "unit": vs.unit,
                        "source_type": vs.source_type.value,
                        "source": "compute_chain_totals",
                    }
                )

        # 10) Legacy HourRow + print (debug)
        out.append(
            HourRow(
                time_iso=t.isoformat(),
                market=market,
                price_eur_per_mwh=float(price_vs.value),
                electrolyzer_on=bool(control_vs.value),
                exergy_destruction_total=ex_dest_val,
            )
        )

        print(
            t.isoformat(),
            "price=", float(price_vs.value),
            "T_amb_K=", float(T_amb_vs.value),
            "on=", bool(control_vs.value),
            "storage=", float(storage_vs.value),
            "Ex_dest_total=", ex_dest_val,
        )

    # 11) Write Phase 5.5 CSV export
    out_dir = "data/cache/timeseries"
    start_tag = start_utc.date().isoformat()
    end_tag = end_utc.date().isoformat()
    csv_path = f"{out_dir}/hourly_timeseries_{market}_{start_tag}_{end_tag}.csv"

    written = rows_to_csv(rows=rows, path=csv_path)
    print("WROTE TIMESERIES CSV:", written)

    return out


def main() -> None:
    start = datetime(2022, 1, 1, 0, 0, tzinfo=timezone.utc)
    end = datetime(2022, 1, 1, 3, 0, tzinfo=timezone.utc)
    run_hourly_minimal_exergy(start, end, market="DE-LU")


if __name__ == "__main__":
    main()
