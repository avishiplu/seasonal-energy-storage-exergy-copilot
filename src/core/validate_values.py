from __future__ import annotations

from .values import ValueSpec, SourceType


def require_source(v: ValueSpec) -> ValueSpec:
    if v is None:
        raise ValueError("ValueSpec is None (missing value).")

    if not isinstance(v, ValueSpec):
        raise ValueError(f"Expected ValueSpec, got {type(v)}")

    if v.source_type is None:
        raise ValueError("Missing source_type on ValueSpec.")

    # ---------------------------
    # EVIDENCE: citation + pdf_name + page mandatory
    # ---------------------------
    if v.source_type == SourceType.EVIDENCE:
        if v.citation is None:
            raise ValueError("Evidence value must include a Citation (pdf_name, page, etc).")

        if not getattr(v.citation, "pdf_name", None):
            raise ValueError("EVIDENCE citation requires pdf_name")

        if getattr(v.citation, "page", None) is None:
            raise ValueError("EVIDENCE citation requires page")

        try:
            int(v.citation.page)
        except Exception:
            raise ValueError("EVIDENCE citation page must be int")

    # ---------------------------
    # COMPUTED: meta.tool mandatory
    # ---------------------------
    if v.source_type == SourceType.COMPUTED:
        if v.meta is None or not isinstance(v.meta, dict):
            raise ValueError("Computed value must include meta dict with tool.")
        tool = v.meta.get("tool")
        if not tool or not isinstance(tool, str):
            raise ValueError("Computed value must include meta['tool'] (string).")

    # ---------------------------
    # ASSUMPTION: meta.note mandatory
    # ---------------------------
    if v.source_type == SourceType.ASSUMPTION:
        if v.meta is None or not isinstance(v.meta, dict):
            raise ValueError("ASSUMPTION requires meta dict with note")
        note = v.meta.get("note")
        if not note or not isinstance(note, str):
            raise ValueError("ASSUMPTION requires meta['note'] (string)")

    # ---------------------------
    # EXTERNAL: meta.source + meta.time_range mandatory
    # ---------------------------
    if v.source_type == SourceType.EXTERNAL:
        if v.meta is None or not isinstance(v.meta, dict):
            raise ValueError("EXTERNAL requires meta dict with source + time_range")
        src = v.meta.get("source")
        tr = v.meta.get("time_range")
        if not src or not isinstance(src, str):
            raise ValueError("EXTERNAL requires meta['source'] (string)")
        if not tr or not isinstance(tr, str):
            raise ValueError("EXTERNAL requires meta['time_range'] (string)")

    return v

