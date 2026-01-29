"""
ingest.py

Task 6 (Chunking implementation)

Goal:
- Load PDFs from data/raw_papers/
- Split (chunk) the extracted text into smaller overlapping pieces
- Print verifiable stats (pages, chunks) + small sample previews

Notes:
- This file does NOT do embeddings or vector-store yet.
- We keep the pipeline step-by-step: Load -> Chunk -> (later) Embed -> Store.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


# ---------- Project paths (robust to running from any working directory) ----------
# PROJECT_ROOT points to the repository root folder: Seasonal_Energy_Storage_App/
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]

# Folder where you keep the cleaned PDFs
PDF_DIR: Path = PROJECT_ROOT / "data" / "raw_papers"


# ---------- Chunking parameters (tunable) ----------
# CHUNK_SIZE: target max length of each chunk (in characters, not tokens)
# CHUNK_OVERLAP: overlap between chunks to avoid losing context at boundaries
CHUNK_SIZE: int = 1000
CHUNK_OVERLAP: int = 150


def load_all_pdfs(pdf_dir: Path) -> List[Document]:
    """
    Load all PDFs from `pdf_dir` and return a flat list of Documents.
    Each Document produced by PyPDFLoader corresponds to a PDF page.

    Adds metadata:
    - source_file: PDF filename
    (PyPDFLoader already adds useful metadata like page index, depending on version.)
    """
    if not pdf_dir.exists():
        raise FileNotFoundError(f"PDF folder does not exist: {pdf_dir}")

    pdf_paths = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_paths:
        raise FileNotFoundError(f"No PDFs found in: {pdf_dir}")

    documents: List[Document] = []
    for pdf_path in pdf_paths:
        loader = PyPDFLoader(str(pdf_path))
        page_docs = loader.load()  # one Document per page

        # Add/normalize metadata for traceability
        for d in page_docs:
            d.metadata["source_file"] = pdf_path.name

        documents.extend(page_docs)

    return documents


def chunk_documents(documents: List[Document]) -> List[Document]:
    """
    Split loaded Documents into chunks using RecursiveCharacterTextSplitter.

    Why RecursiveCharacterTextSplitter?
    - It tries to split at natural boundaries first (paragraphs/newlines),
      and falls back to smaller separators if needed.
    - Produces more readable chunks for retrieval.

    Returns:
    - A list of chunked Documents (each chunk keeps metadata).
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        # Try to preserve structure: paragraphs -> lines -> spaces -> fallback
        separators=["\n\n", "\n", " ", ""],
    )

    chunks = splitter.split_documents(documents)
    return chunks


def print_load_stats(documents: List[Document]) -> None:
    """
    Print simple verifiable stats about loaded pages/documents.
    """
    total_pages = len(documents)
    unique_files = sorted({d.metadata.get("source_file", "UNKNOWN") for d in documents})

    print("\n--- Load result ---")
    print(f"PDF folder: {PDF_DIR}")
    print(f"Total pages loaded (1 doc per page): {total_pages}")
    print(f"Unique PDF files: {len(unique_files)}")
    for f in unique_files:
        print(f"  - {f}")


def print_chunk_stats(chunks: List[Document], sample_count: int = 2) -> None:
    """
    Print chunking configuration, total chunks, and a few sample previews.
    """
    print("\n--- Chunking result ---")
    print(f"Chunk size (chars): {CHUNK_SIZE}")
    print(f"Chunk overlap (chars): {CHUNK_OVERLAP}")
    print(f"Total chunks created: {len(chunks)}")

    # Print a small preview of first N chunks (sanity check)
    for i, c in enumerate(chunks[:sample_count], start=1):
        text = c.page_content.strip().replace("\n", " ")
        print(f"\nSample chunk {i}:")
        print(f"  source_file: {c.metadata.get('source_file')}")
        # Many loaders use 'page' metadata; if not present it will print None
        print(f"  page: {c.metadata.get('page')}")
        print(f"  chars: {len(c.page_content)}")
        print(f"  preview: {text[:200]}...")


def main() -> None:
    """
    Orchestrates:
    1) Load PDFs
    2) Print load stats
    3) Chunk documents
    4) Print chunk stats
    """
    documents = load_all_pdfs(PDF_DIR)
    print_load_stats(documents)

    chunks = chunk_documents(documents)
    print_chunk_stats(chunks, sample_count=2)

    # Next task will start from here:
    # - Embeddings creation
    # - Vector store (FAISS) index build
    # - Persist index to disk


if __name__ == "__main__":
    main()
