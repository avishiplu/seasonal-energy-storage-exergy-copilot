import sys
sys.path.append("src")

import pytest

from src.core.values import assumption_value, external_value
from src.core.refusal import RefusalError
from src.tools.exergy_core import thermal_exergy_of_heat


def test_refuse_when_Tb_below_T0():
    Q = external_value(
        1000.0,
        "J",
        meta={"source": "test", "time_range": "now", "energy_kind": "thermal"},
    )
    Tb = assumption_value(290.0, "K", meta={"note": "Tb below T0"})
    T0 = assumption_value(293.0, "K", meta={"note": "T0"})

    with pytest.raises(RefusalError) as e:
        thermal_exergy_of_heat(Q=Q, Tb_K=Tb, T0_K=T0)

    assert e.value.code == "REFUSE_TB_BELOW_OR_EQUAL_T0"
