# src/retrieval/phase6_runner.py
from __future__ import annotations

import os
import re
from typing import Dict, List, Set, Tuple

try:
    # Optional module (preferred). If not present, fallback keeps build stable.
    from src.retrieval.noise_normalize import normalize_equation_text
except Exception:
    def normalize_equation_text(s: str) -> str:
        return s or ""


from src.core.values import Citation
from src.retrieval.component import ComponentType
from src.retrieval.required_inputs import required_inputs_for
from src.retrieval.query_templates import build_queries
from src.retrieval.equation_extract import Retriever, retrieve_equations

from src.retrieval.ai_rewrite import ai_rewrite_equation
from src.retrieval.equation_validator import EqTag, validate_equation_candidate
from src.retrieval.equation_conflicts import TaggedEquation, cross_check_conflicts
from src.retrieval.missing_report import InfoItem, InfoStatus, MissingInformationReport


# ------------------------------------------------------------
# ENV FLAGS
# ------------------------------------------------------------
ENABLE_AI = os.getenv("PHASE6_AI_REWRITE", "0") == "1"
ENABLE_DEDUPE = os.getenv("PHASE6_DEDUPE", "1") == "1"
ENABLE_REWRITE_CACHE = os.getenv("PHASE6_REWRITE_CACHE", "1") == "1"
ENABLE_NUMERIC_GUARD = os.getenv("PHASE6_REWRITE_NUM_GUARD", "1") == "1"


# --- simple mapping rules: required_input.key -> expected symbol hints
KEY_HINTS = {
    "eta_el": {"eta_el"},
    "eta_fc": {"eta_fc"},
    "COP": {"COP"},

    # tightened: removed generic "p"
    "p_out_Pa": {"p_out", "p2", "pH2", "p_H2", "outlet pressure"},

    # tightened: removed generic "T"
    "T_out_K": {"T_out", "Tout", "outlet temperature"},

    "T_abs_K": {"T_abs"},
    "T_des_K": {"T_des"},
    "Peq_Pa": {"Peq", "P_eq", "peq"},
    "T0_K": {"T0", "T_0"},
    "Tb_K": {"Tb"},
    "T_supply_K": {"T_supply"},
    "T_heat_K": {"T_heat"},
}


# ------------------------------------------------------------
# DEDUPE + CACHE KEYS (normalized)
# ------------------------------------------------------------
def _candidate_key(ev) -> tuple:
    # Strong identity: pdf + page + chunk_id (preferred)
    pdf = getattr(ev, "pdf_name", None)
    page = int(getattr(ev, "page", -1))
    chunk = getattr(ev, "chunk_id", None)

    if chunk is not None:
        return (pdf, page, str(chunk))

    # Fallback only if chunk_id missing
    raw = (getattr(ev, "equation_text", "") or "")
    norm = " ".join(normalize_equation_text(raw).split())
    return (pdf, page, norm)



def _rewrite_cache_key(raw: str) -> str:
    norm = normalize_equation_text(raw)
    return " ".join(norm.split())


# ------------------------------------------------------------
# NUMERIC HALLUCINATION GUARD
# ------------------------------------------------------------
_NUM_RE = re.compile(r"(?<![A-Za-z])[-+]?\d+(\.\d+)?([eE][-+]?\d+)?")

def _numbers_in(s: str) -> set[str]:
    s2 = normalize_equation_text(s or "")
    return set(m.group(0) for m in _NUM_RE.finditer(s2))

def _rewrite_introduces_new_numbers(raw: str, canon: str) -> bool:
    raw_nums = _numbers_in(raw)
    canon_nums = _numbers_in(canon)
    # allow if canonical only re-formats the SAME numbers
    return len(canon_nums - raw_nums) > 0


# ------------------------------------------------------------
# SAFETY RULE:
# AI / PROPOSED equations never auto-FOUND
# ------------------------------------------------------------
def _status_from_eqtags(tags: List[EqTag]) -> InfoStatus:
    if not tags:
        return InfoStatus.MISSING
    if any(t == EqTag.CONFLICT for t in tags):
        return InfoStatus.CONFLICT
    if any(t == EqTag.AMBIGUOUS for t in tags) or any(t == EqTag.PROPOSED for t in tags):
        return InfoStatus.AMBIGUOUS
    if all(t == EqTag.VALID for t in tags):
        return InfoStatus.FOUND
    return InfoStatus.PARTIAL


def run_phase6_for_component(
    retriever: Retriever,
    component: ComponentType,
    component_label: str,
    quantity_targets: List[str],
    allowed_variables: Set[str],
) -> Dict[str, object]:

    reqs = required_inputs_for(component)

    # ------------------------------------------------------------
    # 1) Build queries
    # ------------------------------------------------------------
    queries: List[str] = []
    for q in quantity_targets:
        queries.extend(build_queries(component_label, q))

    tagged: List[TaggedEquation] = []
    evidence_for_key: Dict[str, List[tuple[EqTag, Citation]]] = {}

    # Dedup across ALL query variants (same pdf/page/equation_text normalized)
    seen_candidates: Set[tuple] = set()

    # Cache rewrite results to avoid repeated LLM calls for same raw text (normalized)
    rewrite_cache: Dict[str, tuple[str, str | None]] = {}


    # ------------------------------------------------------------
    # 2) Retrieve → Extract → Validate → (AI Rewrite optional)
    # ------------------------------------------------------------
    for q in queries:
        evidences = retrieve_equations(retriever=retriever, query=q, k=8)

        # ------------------------------------------------------------
        # DEDUPE: same candidate can appear for many query variants
        # ------------------------------------------------------------
        if ENABLE_DEDUPE:
            unique_evidences = []
            for ev in evidences:
                k0 = _candidate_key(ev)
                if k0 in seen_candidates:
                    continue
                seen_candidates.add(k0)
                unique_evidences.append(ev)
            evidences = unique_evidences

        for ev in evidences:
            v_raw = validate_equation_candidate(
                ev.equation_text,
                allowed_variables=allowed_variables,
            )

            final_v = v_raw
            ai_notes = None

            # --- rewrite metadata (spec 6.3B) ---
            rewrite_flag = False
            original_equation = None
            rewrite_confidence = None

            # Only run rewrite if AMBIGUOUS (spec 6.3/6.4 guard)
            if ENABLE_AI and v_raw.tag == EqTag.AMBIGUOUS:
                ctx = getattr(ev, "context_snippet", "") or ""

                # store raw/original equation (spec 6.3B)
                original_equation = ev.equation_text

                # cache lookup
                raw_key = _rewrite_cache_key(ev.equation_text)
                if ENABLE_REWRITE_CACHE and raw_key in rewrite_cache:
                    r = rewrite_cache[raw_key]
                else:
                    print("AI rewrite call starting for:", ev.pdf_name, ev.page)
                    r = ai_rewrite_equation(ev.equation_text, ctx)

                    # AI may return multiple equations separated by newlines
                    rewritten_lines = []
                    if r.canonical_ascii and r.canonical_ascii != "UNSURE":
                        for ln in r.canonical_ascii.splitlines():
                            ln = ln.strip()
                            if ln:
                                rewritten_lines.append(ln)
                    print("AI rewrite done.")
                    if ENABLE_REWRITE_CACHE:
                        rewrite_cache[raw_key] = r

                canon = (getattr(r, "canonical_ascii", None) or "").strip()

                # HARD SAFETY: reject hallucinated numeric constants
                if (
                    ENABLE_NUMERIC_GUARD
                    and canon
                    and canon != "UNSURE"
                    and original_equation is not None
                    and _rewrite_introduces_new_numbers(original_equation, canon)
                ):
                    canon = "UNSURE"
                    rewrite_flag = False
                    # keep a visible note
                    ai_notes = (getattr(r, "notes", None) or "")
                    ai_notes = (ai_notes + " | " if ai_notes else "") + (
                        "REWRITE_REJECTED: introduced numeric values not present in source text."
                    )

                # Accept rewrite only if still not UNSURE
                if canon and canon != "UNSURE":
                    rewrite_flag = True  # rewrite accepted (spec 6.3B)

                    v_ai = validate_equation_candidate(
                        canon,
                        allowed_variables=allowed_variables,
                    )
                    final_v = v_ai

                    # prefer existing ai_notes (may include REWRITE_REJECTED), else r.notes
                    if ai_notes is None:
                        ai_notes = getattr(r, "notes", None)

                    # Optional future support:
                    # rewrite_confidence = getattr(r, "confidence", None)

            # citation unchanged (spec)
            cit = Citation(
                pdf_name=ev.pdf_name,
                page=int(ev.page),
                chunk_id=ev.chunk_id,
                short_quote=None,
            )

            note_text = (
                "; ".join(i.message for i in final_v.issues)
                if final_v.issues
                else None
            )
            if ai_notes:
                note_text = (note_text + " | " if note_text else "") + ai_notes

            tagged.append(
                TaggedEquation(
                    name=f"{component_label}:{q[:30]}",
                    canonical=final_v.canonical,
                    tag=final_v.tag,
                    notes=note_text,
                    rewrite_flag=rewrite_flag,
                    original_equation=original_equation,
                    rewrite_confidence=rewrite_confidence,
                )
            )

            # --------------------------------------------------------
            # 3) Mapping: vars + canonical text
            # --------------------------------------------------------
            canon_text = final_v.canonical or ""
            vars_text = " ".join(sorted(final_v.variables)) if final_v.variables else ""

            for r_req in reqs:
                hints = KEY_HINTS.get(r_req.key, set())
                if not hints:
                    continue

                if (
                    any(h in final_v.variables for h in hints)
                    or any(h in canon_text for h in hints)
                    or any(h in vars_text for h in hints)
                ):
                    evidence_for_key.setdefault(r_req.key, []).append((final_v.tag, cit))

    # ------------------------------------------------------------
    # 4) Cross-check conflicts
    # ------------------------------------------------------------
    tagged = cross_check_conflicts(tagged)

    # ------------------------------------------------------------
    # 5) Missing information report
    # ------------------------------------------------------------
    items: List[InfoItem] = []

    for r_req in reqs:
        refs = evidence_for_key.get(r_req.key, [])
        tags = [t for (t, _c) in refs]

        status = _status_from_eqtags(tags)
        pdf = page = why = None

        if status == InfoStatus.MISSING:
            why = "No extracted or reconstructed equation matched this key."
        else:
            _, c0 = refs[0]
            pdf = c0.pdf_name
            page = c0.page

        items.append(
            InfoItem(
                key=r_req.key,
                unit=r_req.unit,
                status=status,
                critical=r_req.critical,
                why=why,
                citation_pdf=pdf,
                citation_page=page,
            )
        )

    return {
        "equations": tagged,
        "report": MissingInformationReport(
            component=component.value,
            items=items,
        ),
    }
