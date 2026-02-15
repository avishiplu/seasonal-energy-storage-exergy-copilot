# src/retrieval/equation_validator.py
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Set, Tuple

from src.retrieval.noise_normalize import normalize_pdf_noise


class EqTag(str, Enum):
    VALID = "VALID"
    PROPOSED = "PROPOSED"
    AMBIGUOUS = "AMBIGUOUS"
    CONFLICT = "CONFLICT"
    INVALID = "INVALID"


@dataclass(frozen=True)
class EqIssue:
    code: str
    message: str


@dataclass(frozen=True)
class EqValidationResult:
    tag: EqTag
    variables: Set[str]
    issues: List[EqIssue]
    canonical: str


_VAR_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_]*\b")
_BAD_TOKENS = {
    "Eq", "EQ", "equation", "Equation", "Formel", "Gl", "siehe", "see",
    "and", "or", "with", "where", "for",
}


def _canonicalize(text: str) -> str:
    # One locked place for PDF/OCR noise normalization
    return normalize_pdf_noise(text)


def _split_lhs_rhs(eq: str) -> Optional[Tuple[str, str]]:
    if "=" not in eq:
        return None
    lhs, rhs = eq.split("=", 1)
    lhs = lhs.strip()
    rhs = rhs.strip()
    if not lhs or not rhs:
        return None
    return lhs, rhs


def _extract_vars(eq: str) -> Set[str]:
    toks = set(_VAR_RE.findall(eq))
    out = set()
    for tok in toks:
        if tok in _BAD_TOKENS:
            continue
        # filter obvious functions/units
        if tok in {"ln", "log", "exp", "sin", "cos", "tan"}:
            continue
        out.add(tok)
    return out


def _case_mismatch(vars_: Set[str]) -> Optional[str]:
    # EX vs Ex vs ex
    by_lower = {}
    for v in vars_:
        lo = v.lower()
        by_lower.setdefault(lo, set()).add(v)
    clashes = [sorted(list(s)) for s in by_lower.values() if len(s) > 1]
    if clashes:
        return f"Case-mismatch symbols: {clashes[:3]}"
    return None


def validate_equation_candidate(
    raw_text: str,
    allowed_variables: Optional[Set[str]] = None,
) -> EqValidationResult:
    issues: List[EqIssue] = []
    canon = _canonicalize(raw_text)

    # 1) basic structure
    split = _split_lhs_rhs(canon)
    if split is None:
        # could be fragment (AMBIGUOUS) or junk (INVALID)
        if "=" in canon:
            issues.append(EqIssue("MISSING_SIDE", "Equation has '=' but missing LHS or RHS."))
            tag = EqTag.AMBIGUOUS
        else:
            issues.append(EqIssue("NO_EQUALS", "No '=' found; likely fragment."))
            tag = EqTag.AMBIGUOUS

        vars_ = _extract_vars(canon)

        # if almost no symbols, treat as INVALID
        if len(vars_) < 2:
            issues.append(EqIssue("TOO_FEW_SYMBOLS", "Too few variables/symbols to be an equation."))
            tag = EqTag.INVALID

        return EqValidationResult(tag=tag, variables=vars_, issues=issues, canonical=canon)

    lhs, rhs = split

    # 1.5) Reject sentence-like LHS even if it contains '=' (Task 6.4 fix)
    lhs_tokens = lhs.split()
    if len(lhs_tokens) > 5:
        issues.append(EqIssue("TEXT_LHS", "LHS looks like sentence/text, not a symbol expression."))

    # 2) parentheses balance (simple)
    if canon.count("(") != canon.count(")"):
        issues.append(EqIssue("UNBALANCED_PARENS", "Unbalanced parentheses."))

    vars_ = _extract_vars(canon)

    # 3) symbol case mismatch inside same candidate
    cm = _case_mismatch(vars_)
    if cm:
        issues.append(EqIssue("SYMBOL_CASE_MISMATCH", cm))

    # 4) allowed variable gate (stage-wise)
    if allowed_variables is not None and allowed_variables:
        unknown = sorted([v for v in vars_ if v not in allowed_variables])
        if unknown:
            issues.append(EqIssue("UNKNOWN_SYMBOLS", f"Contains symbols not in allowed set: {unknown[:10]}"))

    # 5) decide tag
    if any(i.code == "UNKNOWN_SYMBOLS" for i in issues):
        tag = EqTag.AMBIGUOUS
    elif any(i.code in {"UNBALANCED_PARENS", "SYMBOL_CASE_MISMATCH", "TEXT_LHS"} for i in issues):
        tag = EqTag.AMBIGUOUS
    else:
        tag = EqTag.VALID

    # if lhs/rhs are suspiciously short => fragment
    if len(lhs) < 2 or len(rhs) < 3:
        issues.append(EqIssue("FRAGMENT", "LHS/RHS too short; likely fragment."))
        tag = EqTag.AMBIGUOUS

    return EqValidationResult(
        tag=tag,
        variables=vars_,
        issues=issues,
        canonical=f"{lhs} = {rhs}",
    )
