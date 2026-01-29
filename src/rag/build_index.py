"""
build_index.py

Task 7 (Embeddings + FAISS)

Goal:
- Load PDFs from data/raw_papers/
- Chunk them (same settings as Task 6)
- Create embeddings using OpenAI embeddings API
- Build a FAISS index
- Save index + metadata to disk (data/index/)
"""

from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import List, Dict, Any

import faiss
from dotenv import load_dotenv
from openai import OpenAI

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = PROJECT_ROOT / "data" / "raw_papers"
INDEX_DIR = PROJECT_ROOT / "data" / "index"

# Chunking (same as Task 6)
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

# Embedding model (OpenAI)
EMBED_MODEL = "text-embedding-3-small"

# Batch size: how many chunks we embed per API call
BATCH_SIZE = 64


def load_all_pdfs(pdf_dir: Path) -> List[Document]:
    pdf_paths = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_paths:
        raise FileNotFoundError(f"No PDFs found in: {pdf_dir}")

    documents: List[Document] = []
    for pdf_path in pdf_paths:
        loader = PyPDFLoader(str(pdf_path))
        page_docs = loader.load()  # one Document per page
        for d in page_docs:
            d.metadata["source_file"] = pdf_path.name
        documents.extend(page_docs)

    return documents


def chunk_documents(documents: List[Document]) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )
    return splitter.split_documents(documents)


def embed_texts(client: OpenAI, texts: List[str]) -> List[List[float]]:
    """
    Create embeddings for a list of texts.
    Returns a list of vectors (list[float]) in the same order.
    """
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    # OpenAI returns data items with .embedding
    return [item.embedding for item in resp.data]


def main() -> None:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing. Put it in .env and try again.")

    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    print(f"PDF folder: {PDF_DIR}")
    docs = load_all_pdfs(PDF_DIR)
    print(f"Loaded pages (Documents): {len(docs)}")

    chunks = chunk_documents(docs)
    print(f"Chunks created: {len(chunks)}")
    print(f"Chunking config: size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP}")

    # Prepare texts + metadata for storage
    texts: List[str] = []
    metadatas: List[Dict[str, Any]] = []
    for c in chunks:
        t = c.page_content.strip()
        if not t:
            continue
        texts.append(t)
        metadatas.append({
            "source_file": c.metadata.get("source_file"),
            "page": c.metadata.get("page"),
        })

    print(f"Non-empty chunks to embed: {len(texts)}")

    client = OpenAI()

    # Embed in batches
    vectors: List[List[float]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start:start + BATCH_SIZE]
        batch_vecs = embed_texts(client, batch)
        vectors.extend(batch_vecs)
        print(f"Embedded {min(start + BATCH_SIZE, len(texts))}/{len(texts)}")

    if not vectors:
        raise RuntimeError("No embeddings created (vectors list is empty).")

    dim = len(vectors[0])
    print(f"Embedding dimension: {dim}")

    # Build FAISS index (L2 distance)
    index = faiss.IndexFlatL2(dim)

    # Convert to float32 array for FAISS
    import numpy as np
    xb = np.array(vectors, dtype="float32")
    index.add(xb)

    print(f"FAISS index vectors: {index.ntotal}")

    # Save index + metadata
    index_path = INDEX_DIR / "faiss.index"
    meta_path = INDEX_DIR / "chunks_meta.pkl"

    faiss.write_index(index, str(index_path))
    with open(meta_path, "wb") as f:
        pickle.dump({"texts": texts, "metadatas": metadatas}, f)

    print("\n--- Saved ---")
    print(f"FAISS index: {index_path}")
    print(f"Chunk metadata: {meta_path}")

    # Acceptance check
    if index.ntotal != len(texts):
        raise RuntimeError("Mismatch: FAISS vector count != number of embedded chunks.")

    print("\n✅ Task 7 Step 2 complete: embeddings + FAISS built & saved.")


if __name__ == "__main__":
    main()
