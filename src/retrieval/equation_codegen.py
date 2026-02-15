from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set

from src.core.values import Citation  # uses your existing Citation dataclass


class EquationStatus(str, Enum):
    FOUND = "FOUND"
    AMBIGUOUS = "AMBIGUOUS"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class EquationSpec:
    name: str
    raw: str
    variables: List[str]
    citation: Citation
    status: EquationStatus
    notes: Optional[str] = None


_VAR_RE = re.compile(r"\b[a-zA-Z_]\w*\b")

def _extract_vars(eq: str) -> List[str]:
    toks = _VAR_RE.findall(eq)
    # remove common words / units / functions
    blacklist = {
        "if", "else", "for", "and", "or",
        "sin", "cos", "tan", "log", "ln", "exp", "sqrt",
        "min", "max",
    }
    # keep order but unique
    seen: Set[str] = set()
    out: List[str] = []
    for t in toks:
        if t in blacklist:
            continue
        if t.isupper() and len(t) <= 3:
            # Often "Eq" or "PDF" noise; keep conservative
            pass
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out

def validate_variables(variables: List[str], allowed: Set[str]) -> Optional[str]:
    unknown = [v for v in variables if v not in allowed]
    if unknown:
        return f"Unknown variables found: {unknown}"
    return None

def normalize_equation(eq: str) -> str:
    s = eq.strip()
    s = s.replace("−", "-").replace("·", "*")
    s = re.sub(r"\s+", "", s)
    return s

def cross_check_equations(eqs: List[EquationSpec]) -> List[EquationSpec]:
    """
    If same 'name' appears with different normalized form -> mark AMBIGUOUS.
    """
    by_name: Dict[str, Dict[str, List[EquationSpec]]] = {}
    for e in eqs:
        n = normalize_equation(e.raw)
        by_name.setdefault(e.name, {}).setdefault(n, []).append(e)

    out: List[EquationSpec] = []
    for name, forms in by_name.items():
        if len(forms) == 1:
            out.extend([e for group in forms.values() for e in group])
            continue

        # multiple different forms => ambiguous
        for group in forms.values():
            for e in group:
                out.append(
                    EquationSpec(
                        name=e.name,
                        raw=e.raw,
                        variables=e.variables,
                        citation=e.citation,
                        status=EquationStatus.AMBIGUOUS,
                        notes="Multiple conflicting equation forms found across PDF chunks (symbol mismatch).",
                    )
                )
    return out

def equation_to_python_template(
    eq: EquationSpec,
    func_name: str,
    unit_notes: str,
) -> str:
    """
    Generates a safe *template* (NOT executing parsing math).
    Developer manually fills the RHS safely later.
    """
    args = ", ".join(eq.variables) if eq.variables else ""
    doc = (
        f'"""\n'
        f"Equation: {eq.raw}\n"
        f"Citation: {eq.citation.pdf_name} p.{eq.citation.page}\n"
        f"Unit notes: {unit_notes}\n"
        f'"""\n'
    )
    body = (
        "    # TODO: Implement RHS safely.\n"
        "    # IMPORTANT: Do NOT trust raw PDF text as executable code.\n"
        "    raise NotImplementedError('Implement equation safely after verification.')\n"
    )
    return f"def {func_name}({args}):\n{doc}{body}"
