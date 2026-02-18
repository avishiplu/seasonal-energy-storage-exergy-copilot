from __future__ import annotations

from src.core.values import ValueSpec, assumption_value
from src.simulation.stage import Stage, StageType
from src.simulation.stage_chain import StageChain


def build_stage_chain_ptes(
    Q_delivered_J: ValueSpec,

    Tb_DH_K: ValueSpec,     # DH boundary temperature
    T_store_K: ValueSpec,   # storage temperature
    T0_K: ValueSpec,        # ambient reference

    eta_collector: ValueSpec,
    A_collector_m2: ValueSpec,
    G_solar_Wm2: ValueSpec,
    t_operation_s: ValueSpec,

    UA_WK: ValueSpec,
    t_storage_s: ValueSpec,

    COP: ValueSpec,
) -> StageChain:

    # ---------------------------------------------------------
    # 1) SOLAR COLLECTION
    # ---------------------------------------------------------
    Q_solar_J = assumption_value(
        value=float(G_solar_Wm2.value)
        * float(A_collector_m2.value)
        * float(t_operation_s.value),
        unit="J",
        meta={"note": "Q_solar = G * A * t_operation"},
    )

    Q_collected_J = assumption_value(
        value=float(eta_collector.value) * float(Q_solar_J.value),
        unit="J",
        meta={"note": "Q_collected = eta * Q_solar"},
    )

    Q_collect_loss_J = assumption_value(
        value=max(float(Q_solar_J.value) - float(Q_collected_J.value), 0.0),
        unit="J",
        meta={"note": "Collector optical/thermal losses"},
    )

    # ---------------------------------------------------------
    # 2) SEASONAL STORAGE LOSS
    # ---------------------------------------------------------
    deltaT = max(float(T_store_K.value) - float(T0_K.value), 0.0)

    Q_storage_loss_J = assumption_value(
        value=float(UA_WK.value) * deltaT * float(t_storage_s.value),
        unit="J",
        meta={"note": "Q_loss = UA * (T_store - T0) * t_storage"},
    )

    Q_stored_J = assumption_value(
        value=max(float(Q_collected_J.value) - float(Q_storage_loss_J.value), 0.0),
        unit="J",
        meta={"note": "Q_stored after seasonal loss"},
    )

    # ---------------------------------------------------------
    # 3) HEAT PUMP ENERGY BALANCE
    # ---------------------------------------------------------
    cop_val = max(float(COP.value), 1e-9)

    E_el_in_J = assumption_value(
        value=float(Q_delivered_J.value) / cop_val,
        unit="J",
        meta={"note": "Electric input from COP"},
    )

    Q_source_J = assumption_value(
        value=max(float(Q_delivered_J.value) - float(E_el_in_J.value), 0.0),
        unit="J",
        meta={"note": "Heat extracted from storage"},
    )

    # Feasibility check
    if float(Q_stored_J.value) < float(Q_source_J.value):
        raise ValueError(
            f"PTES infeasible: Q_stored ({Q_stored_J.value}) "
            f"< Q_source ({Q_source_J.value}). "
            "Increase collector area or reduce storage losses."
        )

    # ---------------------------------------------------------
    # STAGES
    # ---------------------------------------------------------

    # Stage 1 — Collector
    s1 = Stage(
        name="COLLECT_SOLAR",
        stage_type=StageType.CHARGE,
        inputs={"heat_in": Q_solar_J},
        outputs={"heat_out": Q_collected_J},
        losses={"heat_loss": Q_collect_loss_J},
        Tb_K=T_store_K,
        computed={},
    )

    # Stage 2 — Storage
    s2 = Stage(
        name="STORE_THERMAL",
        stage_type=StageType.STORE,
        inputs={"heat_in": Q_collected_J},
        outputs={"heat_out": Q_stored_J},
        losses={"heat_loss": Q_storage_loss_J},
        Tb_K=T_store_K,
        computed={},
    )

    # Stage 3a — Extract from storage (same temperature level)
    s3a = Stage(
        name="EXTRACT_FROM_STORAGE",
        stage_type=StageType.CONVERT,
        inputs={"heat_in": Q_stored_J},
        outputs={"heat_out": Q_source_J},
        losses={},
        Tb_K=T_store_K,
        computed={},
    )

    # Stage 3b — Heat pump upgrade (electricity raises quality)
    s3b = Stage(
        name="HEAT_PUMP_UPGRADE",
        stage_type=StageType.CONVERT,
        inputs={"electricity_in": E_el_in_J, "heat_in": Q_source_J},
        outputs={"heat_out": Q_delivered_J},
        losses={},
        Tb_K=Tb_DH_K,
        computed={},
    )

    # Stage 4 — Delivery
    s4 = Stage(
        name="DELIVER_DH",
        stage_type=StageType.DELIVER,
        inputs={"heat_in": Q_delivered_J},
        outputs={"heat_out": Q_delivered_J},
        losses={},
        Tb_K=Tb_DH_K,
        computed={},
    )

    chain = StageChain(stages=[s1, s2, s3a, s3b, s4])
    chain.validate()
    return chain
