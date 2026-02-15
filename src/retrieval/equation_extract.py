from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Protocol


@dataclass(frozen=True)
class Chunk:
    text: str
    pdf_name: str
    page: int
    chunk_id: Optional[str] = None


class Retriever(Protocol):
    def search(self, query: str, k: int = 8) -> List[Chunk]: ...


@dataclass(frozen=True)
class EquationEvidence:
    equation_text: str
    pdf_name: str
    page: int
    chunk_id: Optional[str]
    context_snippet: str


# -----------------------------
# Candidate detection patterns
# -----------------------------

# 1) "=" style equation line (relaxed length; allow long lines too)
_EQ_RE = re.compile(
    r"""
    (?:
      ^|\n
    )
    ([^\n]{0,800}
      =
     [^\n]{0,800}
    )
    """,
    re.VERBOSE,
)

# 2) Equation labels commonly used in German/English PDFs
_EQ_LABEL_RE = re.compile(r"\b(Eq\.|Equation|Gl\.|Gleichung|Formel)\b", re.IGNORECASE)

# 3) Symbol-heavy hint lines (fallback)
_SYMBOL_HINT_RE = re.compile(r"(T0\s*/\s*T|η|Δ|_|\^|/|·|×|\*|ln|log|exp)", re.IGNORECASE)

# 4) Avoid capturing obvious prose-only lines
_PROSE_STOP_RE = re.compile(r"^[A-Za-zÄÖÜäöüß ,;\-]{25,}$")

# 5) Strong math markers (better than only '=') — include '=' too
_STRONG_MATH_RE = re.compile(r"(=|≈|≃|≤|≥|→|±|∑|∫|√|¼)")

# 6) Very common "units" hints
_UNIT_HINT_RE = re.compile(r"\b(K|Pa|bar|W|kW|MW|J|kJ|MJ|GJ|kg|mol|m3|s)\b")


def _looks_like_formula(line: str) -> bool:
    """
    Decide whether a line is formula-like enough to keep.
    Relaxed for sprint/demo + synthetic PDFs:
    - allow short equations like 'COP = COP'
    - do NOT require digits
    - accept any '=' lines unless they are obvious prose
    """
    line = (line or "").strip()

    # Very short or empty -> reject
    if len(line) < 3:
        return False

    # reject obvious prose-only lines
    if _PROSE_STOP_RE.match(line):
        return False

    # If it contains '=' it's almost always a good candidate in our setting
    if "=" in line:
        return True

    # keep lines with strong math markers or explicit equation labels
    if _STRONG_MATH_RE.search(line) or _EQ_LABEL_RE.search(line):
        return True

    # fallback: symbol-heavy lines
    if _SYMBOL_HINT_RE.search(line):
        return True

    # fallback: unit hint + symbol hint
    if _UNIT_HINT_RE.search(line) and _SYMBOL_HINT_RE.search(line):
        return True

    return False


def extract_equation_lines(text: str) -> List[str]:
    out: List[str] = []

    # A) strict "=" lines
    for m in _EQ_RE.findall(text):
        s = (m or "").strip()
        if s and _looks_like_formula(s):
            out.append(s)

    # B) label-based lines (Eq./Gl./Formel etc.)
    for raw in text.splitlines():
        line = (raw or "").strip()
        if not line:
            continue
        if _EQ_LABEL_RE.search(line) and _looks_like_formula(line):
            out.append(line)

    # C) symbol-heavy fallback
    for raw in text.splitlines():
        line = (raw or "").strip()
        if not line:
            continue
        if _SYMBOL_HINT_RE.search(line) and _looks_like_formula(line):
            out.append(line)

    # De-duplicate preserving order
    seen = set()
    uniq: List[str] = []
    for s in out:
        if s not in seen:
            seen.add(s)
            uniq.append(s)

    return uniq


def retrieve_equations(
    retriever: Retriever,
    query: str,
    k: int = 8,
) -> List[EquationEvidence]:
    chunks = retriever.search(query=query, k=k)

    out: List[EquationEvidence] = []
    for ch in chunks:
        eqs = extract_equation_lines(ch.text)
        for eq in eqs:
            ctx = (ch.text or "").strip()
            if len(ctx) > 280:
                ctx = ctx[:280] + "..."
            out.append(
                EquationEvidence(
                    equation_text=eq,
                    pdf_name=ch.pdf_name,
                    page=int(ch.page),
                    chunk_id=ch.chunk_id,
                    context_snippet=ctx,
                )
            )
    return out
