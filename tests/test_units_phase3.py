import pytest

from src.core.values import external_value, assumption_value
from src.tools.exergy_core import thermal_exergy_of_heat
from src.core.refusal import RefusalError


def test_exergy_accepts_celsius_and_kwh():
    Q = external_value(
        1.0,
        "kWh",
        meta={"source": "t", "time_range": "now", "energy_kind": "thermal"},
    )
    Tb = assumption_value(80.0, "°C", meta={"note": "Tb"})
    T0 = assumption_value(20.0, "°C", meta={"note": "T0"})

    ex = thermal_exergy_of_heat(Q=Q, Tb_K=Tb, T0_K=T0)

    assert ex.unit == "J"
    assert ex.meta["tool"] == "thermal_exergy_of_heat"


def test_refuse_kwh_without_energy_kind():
    Q = external_value(
        1.0,
        "kWh",
        meta={"source": "t", "time_range": "now"},  # missing energy_kind
    )
    Tb = assumption_value(353.15, "K", meta={"note": "Tb"})
    T0 = assumption_value(293.15, "K", meta={"note": "T0"})

    with pytest.raises(RefusalError):
        thermal_exergy_of_heat(Q=Q, Tb_K=Tb, T0_K=T0)
