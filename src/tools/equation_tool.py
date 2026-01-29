# src/equation_tool.py

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from pathlib import Path
import re

import fitz  # PyMuPDF


from dataclasses import dataclass
from typing import Optional, List, Dict

@dataclass
class EquationHit:
    latex: str
    ascii: str
    source_file: str
    page: int
    evidence_lines: List[str]

    # Optional / future-ready fields
    machine_expr: Optional[str] = None
    json: Optional[Dict] = None




# ----------------------------
# Helpers
# ----------------------------

def _clean_line(text: str) -> str:
    text = text.replace("\u2212", "-")  # normalize unicode minus
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _looks_like_equation(line: str) -> bool:
    if len(line) < 12:
        return False

    if "=" in line and any(
        token in line for token in ["+", "-", "*", "/", "ln", "log", "exp", "Δ", "(", ")"]
    ):
        return True

    if re.search(r"\bEq\.?\s*\(?\d+\)?", line, flags=re.IGNORECASE):
        return True

    if (
        ("ln" in line or "log" in line)
        and ("P" in line or "Peq" in line or "P_eq" in line)
        and ("ΔH" in line or "DeltaH" in line)
    ):
        return True

    return False


def _normalize_to_ascii(raw: str) -> str:
    text = raw
    text = text.replace("ΔH", "DeltaH")
    text = text.replace("ΔS", "DeltaS")
    text = text.replace("◦C", "°C")
    return _clean_line(text)


def _best_effort_to_latex(ascii_eq: str) -> str:
    latex = ascii_eq

    # subscripts: P_eq -> P_{eq}
    latex = re.sub(r"\b([A-Za-z]+)_([A-Za-z0-9]+)\b", r"\1_{\2}", latex)

    latex = latex.replace("ln(", r"\ln\left(")
    latex = latex.replace(")", r"\right)")

    latex = latex.replace("DeltaH", r"\Delta H")
    latex = latex.replace("DeltaS", r"\Delta S")

    latex = re.sub(
        r"\\Delta H\s*/\s*\(\s*R\s*\*\s*T\s*\)",
        r"\\frac{\\Delta H}{R T}",
        latex,
    )

    latex = re.sub(
        r"\\Delta S\s*/\s*R",
        r"\\frac{\\Delta S}{R}",
        latex,
    )

    return latex


def _extract_equation_blocks(text: str, window: int = 1) -> List[List[str]]:
    lines = [_clean_line(l) for l in text.splitlines() if _clean_line(l)]
    blocks: List[List[str]] = []

    for i, line in enumerate(lines):
        if _looks_like_equation(line):
            start = max(0, i - window)
            end = min(len(lines), i + window + 1)
            blocks.append(lines[start:end])

    return blocks


# ----------------------------
# Main tool function
# ----------------------------

def retrieve_equations(
    pdf_paths: List[str],
    query: str,
    max_hits: int = 5,
) -> Dict[str, Any]:

    query_tokens = re.findall(r"[A-Za-z0-9Δ]+", query.lower())

    hits: List[EquationHit] = []

    for pdf_path in pdf_paths:
        path = Path(pdf_path)
        doc = fitz.open(str(path))

        for page_index in range(doc.page_count):
            page = doc.load_page(page_index)
            text = page.get_text("text")

            if not text:
                continue

            blocks = _extract_equation_blocks(text)

            for block in blocks:
                joined = " ".join(block).lower()

                if query_tokens:
                    if not any(tok in joined for tok in query_tokens):
                        continue

                raw = " ".join(block)
                ascii_eq = _normalize_to_ascii(raw)
                latex_eq = _best_effort_to_latex(ascii_eq)

                json_eq: Dict[str, Any] = {
                    "raw": raw,
                    "ascii": ascii_eq,
                    "lhs": None,
                    "rhs": None,
                }

                if "=" in ascii_eq:
                    left, right = ascii_eq.split("=", 1)
                    json_eq["lhs"] = left.strip()
                    json_eq["rhs"] = right.strip()

                hits.append(
                    EquationHit(
                        source_file=path.name,
                        page=page_index,
                        evidence_lines=block,
                        latex=latex_eq,
                        ascii=ascii_eq,
                        json=json_eq,
                    )
                )

    # Deduplicate
    unique_hits: List[EquationHit] = []
    seen = set()

    for h in hits:
        key = (h.source_file, h.page, h.ascii)
        if key not in seen:
            seen.add(key)
            unique_hits.append(h)

    unique_hits = unique_hits[:max_hits]

    return {
        "query": query,
        "hits": [asdict(h) for h in unique_hits],
        "citations": [
            {"source_file": h.source_file, "page": h.page}
            for h in unique_hits
        ],
    }


    # 2) OCR fallback (from equations/service.py)
    from equations.service import extract_math_from_pdf

    ocr_hits = []
    citations = []

    for pdf_path in pdf_paths:
        ocr_results = extract_math_from_pdf(pdf_path=pdf_path, max_pages=ocr_max_pages)

        for r in ocr_results:
            ocr_hits.append({
                "latex": r["latex"],
                "ascii": r["latex"],
                "source_file": pdf_path.split("/")[-1],
                "page": r["page_index"],  # 0-based
                "evidence_lines": ["(OCR extracted from scanned/image PDF)"],
                "machine_expr": None,
                "json": {
                    "raw": r["latex"],
                    "ascii": r["latex"],
                    "lhs": None,
                    "rhs": None,
                    "confidence": r.get("confidence"),
                    "provenance": r.get("provenance"),
                },
            })
            citations.append({"source_file": pdf_path.split("/")[-1], "page": r["page_index"]})

            if len(ocr_hits) >= max_hits:
                break

        if len(ocr_hits) >= max_hits:
            break

    return {
        "query": query,
        "hits": ocr_hits,
        "citations": citations,
        "method": "ocr_fallback",
    }
