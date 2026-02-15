# src/retrieval/noise_normalize.py
from __future__ import annotations
import re

REPLACEMENTS = [
    ("¼", "="),      # equals
    ("/C0", "-"),    # minus
    ("/C14", "°"),   # degree
    ("−", "-"),
    ("–", "-"),
    ("—", "-"),
    ("×", "*"),
    ("·", "*"),
]

def normalize_pdf_noise(text: str) -> str:
    t = (text or "").strip()
    for a, b in REPLACEMENTS:
        t = t.replace(a, b)
    t = re.sub(r"\s+", " ", t)
    return t.strip()
