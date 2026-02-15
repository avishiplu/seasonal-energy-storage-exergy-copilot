"""
retriever.py

Task 8 — Retriever Logic (Top-K Similarity Search)

Purpose
-------
Semantic similarity search over a persisted FAISS vector store
and returns relevant text chunks with source metadata.
"""

from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import List, Dict, Any, Tuple

import faiss
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI


# ---------------------------------------------------------------------------
# Project paths (repo-root based; no cwd dependency)
# retriever.py: <root>/src/rag/retriever.py
# parents[0]=rag, parents[1]=src, parents[2]=<root>
# ---------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
INDEX_DIR: Path = PROJECT_ROOT / "data" / "index"

INDEX_PATH: Path = INDEX_DIR / "faiss.index"
META_PATH: Path = INDEX_DIR / "chunks_meta.pkl"  # must match build_index.py output


# ---------------------------------------------------------------------------
# Retrieval configuration
# ---------------------------------------------------------------------------
EMBED_MODEL: str = "text-embedding-3-small"
TOP_K: int = 3


# ---------------------------------------------------------------------------
# Core loading utilities
# ---------------------------------------------------------------------------
def load_index_and_metadata() -> Tuple[faiss.Index, Dict[str, Any]]:
    if not INDEX_PATH.exists():
        raise FileNotFoundError(f"FAISS index not found: {INDEX_PATH}")
    if not META_PATH.exists():
        raise FileNotFoundError(f"Metadata file not found: {META_PATH}")

    index = faiss.read_index(str(INDEX_PATH))

    with open(META_PATH, "rb") as f:
        meta = pickle.load(f)

    if not isinstance(meta, dict) or "texts" not in meta or "metadatas" not in meta:
        raise RuntimeError("Invalid metadata format. Expected keys: 'texts', 'metadatas'.")

    if len(meta["texts"]) != len(meta["metadatas"]):
        raise RuntimeError("Metadata mismatch: len(texts) != len(metadatas).")

    return index, meta


# ---------------------------------------------------------------------------
# Embedding utilities
# ---------------------------------------------------------------------------
def embed_query(client: OpenAI, query: str) -> np.ndarray:
    response = client.embeddings.create(model=EMBED_MODEL, input=query)
    vector = np.array(response.data[0].embedding, dtype="float32")
    return vector.reshape(1, -1)


# ---------------------------------------------------------------------------
# Retrieval logic
# ---------------------------------------------------------------------------
def retrieve_top_k(query: str, k: int = TOP_K) -> List[Dict[str, Any]]:
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing from environment.")

    index, meta = load_index_and_metadata()

    client = OpenAI()
    query_vector = embed_query(client, query)

    distances, indices = index.search(query_vector, k)

    results: List[Dict[str, Any]] = []
    for rank, idx in enumerate(indices[0], start=1):
        if idx == -1:
            continue
        md = meta["metadatas"][idx]
        results.append(
            {
                "rank": rank,
                "distance": float(distances[0][rank - 1]),
                "text": meta["texts"][idx],
                "source_file": md.get("source_file"),
                "page": md.get("page"),
            }
        )
    return results


def main() -> None:
    test_query = "Eq. (1) COP heat pump"
    results = retrieve_top_k(test_query, k=TOP_K)

    print("\n--- Retrieval Result ---")
    print(f"Query: {test_query}\n")
    for r in results:
        print(f"Rank {r['rank']} | distance={r['distance']:.4f}")
        print(f"Source: {r['source_file']} | page: {r['page']}")
        preview = (r["text"] or "").strip().replace("\n", " ")
        print(f"Text preview: {preview[:300]}...")
        print("-" * 60)


if __name__ == "__main__":
    main()
