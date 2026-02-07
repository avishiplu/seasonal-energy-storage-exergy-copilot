import pytest
from src.core.values import computed_value
from src.core.refusal import RefusalError
from src.tools.exergy_efficiency import exergy_efficiency


def test_efficiency_basic():
    Ex_in = computed_value(1000.0, "J", tool_name="dummy")
    Ex_out = computed_value(400.0, "J", tool_name="dummy")
    eta = exergy_efficiency(Ex_out=Ex_out, Ex_in=Ex_in)
    assert eta.unit == "-"
    assert 0 < eta.value < 1


def test_efficiency_refuse_when_ex_in_nonpositive():
    Ex_in = computed_value(0.0, "J", tool_name="dummy")
    Ex_out = computed_value(100.0, "J", tool_name="dummy")
    with pytest.raises(RefusalError):
        exergy_efficiency(Ex_out=Ex_out, Ex_in=Ex_in)
