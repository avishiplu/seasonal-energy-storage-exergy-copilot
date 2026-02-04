from __future__ import annotations

from src.core.values import ValueSpec

from .stage import Stage, StageType


def electricity_to_hydrogen_stage(
    name: str,
    electricity_in: ValueSpec,
) -> Stage:
    return Stage(
        name=name,
        stage_type=StageType.CONVERT,
        inputs={"electricity_in": electricity_in},
        outputs={},
        losses={},
        Tb_K=None,
        computed={},
    )


def electricity_to_heat_stage(
    name: str,
    electricity_in: ValueSpec,
) -> Stage:
    return Stage(
        name=name,
        stage_type=StageType.CONVERT,
        inputs={"electricity_in": electricity_in},
        outputs={},
        losses={},
        Tb_K=None,
        computed={},
    )


def storage_hold_stage(
    name: str,
    stored_energy: ValueSpec,
) -> Stage:
    return Stage(
        name=name,
        stage_type=StageType.STORE,
        inputs={"stored_energy": stored_energy},
        outputs={},
        losses={},
        Tb_K=None,
        computed={},
    )


def aux_compressor_stage(
    name: str,
    electric_power_in: ValueSpec,
) -> Stage:
    return Stage(
        name=name,
        stage_type=StageType.AUX,
        inputs={"electric_power_in": electric_power_in},
        outputs={},
        losses={},
        Tb_K=None,
        computed={},
    )


def heat_exchanger_to_dh_stage(
    name: str,
    heat_in: ValueSpec,
    Tb_K: ValueSpec,
) -> Stage:
    return Stage(
        name=name,
        stage_type=StageType.DELIVER,
        inputs={"heat_in": heat_in},
        outputs={},
        losses={},
        Tb_K=Tb_K,
        computed={},
    )


def fuel_cell_stage(
    name: str,
    fuel_in: ValueSpec,
) -> Stage:
    return Stage(
        name=name,
        stage_type=StageType.CONVERT,
        inputs={"fuel_in": fuel_in},
        outputs={},
        losses={},
        Tb_K=None,
        computed={},
    )
