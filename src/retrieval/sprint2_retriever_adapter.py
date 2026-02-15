from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from src.rag.retriever import retrieve_top_k


@dataclass(frozen=True)
class Chunk:
    text: str
    pdf_name: str
    page: int
    chunk_id: Optional[str] = None


class Sprint2RetrieverAdapter:
    def search(self, query: str, k: int = 8) -> List[Chunk]:
        rows = retrieve_top_k(query=query, k=k)
        out: List[Chunk] = []
        for r in rows:
            out.append(
                Chunk(
                    text=r.get("text") or "",
                    pdf_name=r.get("source_file") or "UNKNOWN.pdf",
                    page=int(r.get("page") or 0),
                    chunk_id=None,
                )
            )
        return out
