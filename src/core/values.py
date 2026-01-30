from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class SourceType(str, Enum):
    EVIDENCE = "Evidence"
    ASSUMPTION = "Assumption"
    EXTERNAL = "External"
    COMPUTED = "Computed"


@dataclass(frozen=True)
class Citation:
    pdf_name: str
    page: int                 # REQUIRED
    chunk_id: Optional[str] = None
    short_quote: Optional[str] = None


@dataclass(frozen=True)
class ValueSpec:
    value: Any
    unit: str
    source_type: SourceType
    citation: Optional[Citation] = None
    meta: Optional[dict] = None


def evidence_value(value: Any, unit: str, citation: Citation, meta: Optional[dict] = None) -> ValueSpec:
    # enforce page int, even if caller passed something weird
    c = Citation(
        pdf_name=citation.pdf_name,
        page=int(citation.page),
        chunk_id=citation.chunk_id,
        short_quote=citation.short_quote,
    )
    return ValueSpec(
        value=value,
        unit=unit,
        source_type=SourceType.EVIDENCE,
        citation=c,
        meta=meta,
    )

def evidence_value_from_pdf(
    value: Any,
    unit: str,
    pdf_name: str,
    page: int,
    chunk_id: str | None = None,
    short_quote: str | None = None,
    meta: Optional[dict] = None,
) -> ValueSpec:
    return ValueSpec(
        value=value,
        unit=unit,
        source_type=SourceType.EVIDENCE,
        citation=Citation(
            pdf_name=pdf_name,
            page=int(page),
            chunk_id=chunk_id,
            short_quote=short_quote,
        ),
        meta=meta,
    )



def assumption_value(value: Any, unit: str, meta: Optional[dict] = None) -> ValueSpec:
    return ValueSpec(
        value=value,
        unit=unit,
        source_type=SourceType.ASSUMPTION,
        citation=None,
        meta=meta,
    )


def external_value(value: Any, unit: str, meta: Optional[dict] = None) -> ValueSpec:
    return ValueSpec(
        value=value,
        unit=unit,
        source_type=SourceType.EXTERNAL,
        citation=None,
        meta=meta,
    )


def computed_value(value: Any, unit: str, tool_name: str, meta: Optional[dict] = None) -> ValueSpec:
    m = dict(meta or {})
    m["tool"] = tool_name
    return ValueSpec(
        value=value,
        unit=unit,
        source_type=SourceType.COMPUTED,
        citation=None,
        meta=m,
    )
