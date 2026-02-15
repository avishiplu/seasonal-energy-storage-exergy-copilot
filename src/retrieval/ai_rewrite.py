# src/retrieval/ai_rewrite.py
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class AIRewriteResult:
    canonical_ascii: str
    variables: List[str]
    notes: str


# IMPORTANT:
# Phase-6 calls this function per "candidate equation line" (fragment).
# Therefore the rewrite must NOT swap in a different equation from CONTEXT.
# CONTEXT is ONLY for decoding broken OCR/PDF characters.
SYSTEM_PROMPT = """
You are cleaning ONE equation/definition line extracted from a PDF.

You will receive:
- FRAGMENT: one candidate equation line (primary source)
- CONTEXT: nearby text (use ONLY to decode broken characters)

Your job:
1) Normalize obvious PDF noise in the FRAGMENT ONLY (e.g., "¼" -> "=", "/C0" -> "-").
2) Return the cleaned version of THAT SAME FRAGMENT as canonical_ascii.

Hard rules:
- Output JSON ONLY with keys: canonical_ascii, variables, notes
- canonical_ascii must be either:
  - "UNSURE", OR
  - a SINGLE line containing exactly one "=" with non-empty LHS and RHS
- Do NOT invent variables or equations.
- Do NOT merge multiple equations into one line.
- Do NOT replace the FRAGMENT with a different equation from CONTEXT.
- Preserve key tokens EXACTLY IF THEY APPEAR IN THE FRAGMENT:
  p_out_Pa, T_out_K, T_des_K, T_heat_K

variables:
- list variable tokens present in canonical_ascii (best effort).

Return JSON only.
""".strip()


def _strip_code_fences(text: str) -> str:
    t = text.strip()
    # Remove ```json ... ``` fences if present
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    return t.strip()


def _extract_json_object(text: str) -> str:
    """
    Try to recover a JSON object from an LLM response that might contain
    extra text or code fences.
    """
    t = _strip_code_fences(text)

    # Fast path: whole string is JSON
    if t.startswith("{") and t.endswith("}"):
        return t

    # Best-effort: find first {...} block (non-nested safe-ish)
    # We do a simple bracket scan to get the first complete JSON object.
    start = t.find("{")
    if start == -1:
        return ""

    depth = 0
    for i in range(start, len(t)):
        if t[i] == "{":
            depth += 1
        elif t[i] == "}":
            depth -= 1
            if depth == 0:
                return t[start : i + 1].strip()

    return ""


def _best_effort_variables(expr: str) -> List[str]:
    """
    Extract variable-ish tokens from a single equation line.
    This is only a fallback if the model returns bad variables.
    """
    if not expr or expr == "UNSURE":
        return []
    # tokens like eta_el, T_out_K, mH2_dot, LHV_H2, Peq_Pa
    toks = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", expr)
    # Drop obvious function names / constants if you want; keep simple for now.
    # Also keep uniqueness while preserving order.
    seen = set()
    out: List[str] = []
    for tok in toks:
        if tok not in seen:
            seen.add(tok)
            out.append(tok)
    return out


def ai_rewrite_equation(fragment: str, context: str) -> AIRewriteResult:
    # Hard safety: no API key → no crash
    if not os.getenv("OPENAI_API_KEY"):
        return AIRewriteResult(
            canonical_ascii="UNSURE",
            variables=[],
            notes="OPENAI_API_KEY not set; AI rewrite skipped.",
        )

    from openai import OpenAI

    client = OpenAI(timeout=20.0)  # prevents hanging forever

    # Keep the user message minimal and consistent with SYSTEM_PROMPT.
    msg = f"""FRAGMENT:
{fragment}

CONTEXT:
{context}
""".strip()

    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": msg},
        ],
        temperature=0.0,
    )

    raw = (resp.choices[0].message.content or "").strip()
    json_str = _extract_json_object(raw)

    if not json_str:
        # Fail closed (do not crash)
        return AIRewriteResult(
            canonical_ascii="UNSURE",
            variables=[],
            notes=f"AI returned non-JSON; raw_head={raw[:120]!r}",
        )

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        return AIRewriteResult(
            canonical_ascii="UNSURE",
            variables=[],
            notes=f"JSONDecodeError: {e}; raw_head={raw[:120]!r}",
        )

    canonical = str(data.get("canonical_ascii", "")).strip()
    notes = str(data.get("notes", "")).strip()

    variables = data.get("variables", [])
    if not isinstance(variables, list):
        variables = []
    variables = [str(v).strip() for v in variables if str(v).strip()]

    # Additional safety: if model returns empty canonical, mark UNSURE
    if not canonical:
        canonical = "UNSURE"

    # Fallback variables if model didn't give any but canonical exists
    if canonical != "UNSURE" and not variables:
        variables = _best_effort_variables(canonical)

    return AIRewriteResult(
        canonical_ascii=canonical,
        variables=variables,
        notes=notes,
    )
