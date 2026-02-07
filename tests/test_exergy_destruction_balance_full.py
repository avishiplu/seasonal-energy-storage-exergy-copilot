import pytest
from src.core.values import computed_value
from src.core.refusal import RefusalError
from src.tools.exergy_destruction_balance_full import exergy_destruction_balance_full


def test_full_balance_basic():
    Ex_in = computed_value(1000.0, "J", tool_name="dummy")
    Ex_out = computed_value(600.0, "J", tool_name="dummy")
    Ex_dest = exergy_destruction_balance_full(Ex_in=Ex_in, Ex_out=Ex_out)
    assert Ex_dest.unit == "J"
    assert Ex_dest.value == 400.0


def test_full_balance_refuse_negative():
    Ex_in = computed_value(500.0, "J", tool_name="dummy")
    Ex_out = computed_value(600.0, "J", tool_name="dummy")
    with pytest.raises(RefusalError):
        exergy_destruction_balance_full(Ex_in=Ex_in, Ex_out=Ex_out)
