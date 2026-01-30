import sys
sys.path.append("src")

import pytest

from core.values import (
    Citation,
    SourceType,
    ValueSpec,
    computed_value,
    evidence_value,
    assumption_value,
    external_value,
)

from core.validate_values import require_source



def test_evidence_without_citation_fails():
    v = ValueSpec(
        value=0.5,
        unit="-",
        source_type=SourceType.EVIDENCE,
        citation=None,
        meta=None,
    )
    with pytest.raises(ValueError):
        require_source(v)


def test_computed_without_tool_fails():
    v = ValueSpec(
        value=10.0,
        unit="J",
        source_type=SourceType.COMPUTED,
        citation=None,
        meta={},
    )
    with pytest.raises(ValueError):
        require_source(v)


def test_valid_values_pass():
    v1 = evidence_value(
        0.72,
        "-",
        Citation(pdf_name="paper.pdf", page=2),
    )
    v2 = computed_value(
        100.0,
        "J",
        tool_name="dummy_tool",
    )

    require_source(v1)
    require_source(v2)


def test_assumption_without_note_fails():
    v = ValueSpec(
        value=288.15,
        unit="K",
        source_type=SourceType.ASSUMPTION,
        citation=None,
        meta={},  # missing note
    )
    with pytest.raises(ValueError):
        require_source(v)


def test_external_missing_fields_fails():
    v = ValueSpec(
        value=120.0,
        unit="EUR/MWh",
        source_type=SourceType.EXTERNAL,
        citation=None,
        meta={"source": "api"},  # missing time_range
    )
    with pytest.raises(ValueError):
        require_source(v)


def test_valid_assumption_and_external_pass():
    v1 = assumption_value(288.15, "K", meta={"note": "ok"})
    v2 = external_value(5.0, "J", meta={"source": "api", "time_range": "2024"})
    require_source(v1)
    require_source(v2)
