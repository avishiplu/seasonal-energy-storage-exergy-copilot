"""
retriever.py

Task 8 — Retriever Logic (Top-K Similarity Search)

Purpose
-------
This module implements the retrieval layer of the RAG pipeline.
It performs semantic similarity search over a persisted FAISS vector store
and returns the most relevant text chunks together with their source metadata.

Design principles
-----------------
- No LLM generation in this step (retrieval only)
- Full traceability: every retrieved chunk includes source_file and page
- Disk-persisted index is loaded (no re-embedding)
- Minimal, testable, CLI-runnable component
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
# Project paths
# ---------------------------------------------------------------------------
# Resolve paths relative to repository root to avoid dependency on cwd
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
INDEX_DIR: Path = PROJECT_ROOT / "data" / "index"

INDEX_PATH: Path = INDEX_DIR / "faiss.index"
META_PATH: Path = INDEX_DIR / "chunks_meta.pkl"


# ---------------------------------------------------------------------------
# Retrieval configuration
# ---------------------------------------------------------------------------
# Embedding model must match the one used during index construction (Task 7)
EMBED_MODEL: str = "text-embedding-3-small"

# Number of most similar chunks to retrieve
TOP_K: int = 3


# ---------------------------------------------------------------------------
# Core loading utilities
# ---------------------------------------------------------------------------
def load_index_and_metadata() -> Tuple[faiss.Index, Dict[str, Any]]:
    """
    Load the FAISS index and its aligned metadata from disk.

    Returns
    -------
    index : faiss.Index
        FAISS vector index containing embeddings of text chunks.
    meta : dict
        Dictionary containing:
        - "texts": List[str]
        - "metadatas": List[dict] with source_file, page, etc.

    Raises
    ------
    FileNotFoundError
        If index or metadata files are missing.
    """
    if not INDEX_PATH.exists():
        raise FileNotFoundError(f"FAISS index not found: {INDEX_PATH}")
    if not META_PATH.exists():
        raise FileNotFoundError(f"Metadata file not found: {META_PATH}")

    index = faiss.read_index(str(INDEX_PATH))
    with open(META_PATH, "rb") as f:
        meta = pickle.load(f)

    return index, meta


# ---------------------------------------------------------------------------
# Embedding utilities
# ---------------------------------------------------------------------------
def embed_query(client: OpenAI, query: str) -> np.ndarray:
    """
    Convert a natural-language query into an embedding vector.

    Notes
    -----
    - The embedding model must be identical to the one used for indexing.
    - FAISS expects float32 vectors of shape (1, dim).

    Returns
    -------
    np.ndarray
        Query embedding with shape (1, embedding_dim).
    """
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=query,
    )

    vector = np.array(response.data[0].embedding, dtype="float32")
    return vector.reshape(1, -1)


# ---------------------------------------------------------------------------
# Retrieval logic
# ---------------------------------------------------------------------------
def retrieve_top_k(query: str, k: int = TOP_K) -> List[Dict[str, Any]]:
    """
    Perform top-k similarity search for a given query.

    Workflow
    --------
    1. Load FAISS index and aligned metadata
    2. Embed the query text
    3. Run FAISS similarity search
    4. Map retrieved vector indices back to text + metadata

    Parameters
    ----------
    query : str
        User query expressed in natural language.
    k : int
        Number of top similar chunks to retrieve.

    Returns
    -------
    List[dict]
        Each result contains:
        - rank
        - distance (L2 distance from FAISS)
        - text (chunk content)
        - source_file
        - page
    """
    # Load environment variables (API key)
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing from environment.")

    # Load persisted vector store
    index, meta = load_index_and_metadata()

    # Initialize OpenAI client
    client = OpenAI()

    # Embed query
    query_vector = embed_query(client, query)

    # FAISS similarity search
    distances, indices = index.search(query_vector, k)

    # Assemble retrieval results with full traceability
    results: List[Dict[str, Any]] = []
    for rank, idx in enumerate(indices[0], start=1):
        results.append(
            {
                "rank": rank,
                "distance": float(distances[0][rank - 1]),
                "text": meta["texts"][idx],
                "source_file": meta["metadatas"][idx].get("source_file"),
                "page": meta["metadatas"][idx].get("page"),
            }
        )

    return results


# ---------------------------------------------------------------------------
# CLI test entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """
    Minimal CLI test to verify retrieval correctness.

    This function is intentionally simple and deterministic:
    - It runs a single test query
    - Prints ranked results with source attribution
    - No LLM generation involved
    """
    test_query = (
        "What are the advantages of metal hydride based seasonal energy storage?"
    )

    results = retrieve_top_k(test_query, k=TOP_K)

    print("\n--- Retrieval Result ---")
    print(f"Query: {test_query}\n")

    for r in results:
        print(f"Rank {r['rank']} | distance={r['distance']:.4f}")
        print(f"Source: {r['source_file']} | page: {r['page']}")
        preview = r["text"].strip().replace("\n", " ")
        print(f"Text preview: {preview[:300]}...")
        print("-" * 60)


if __name__ == "__main__":
    main()
