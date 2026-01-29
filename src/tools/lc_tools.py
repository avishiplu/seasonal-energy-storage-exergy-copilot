# src/lc_tools.py

from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool

from retriever import retrieve_top_k


class RetrieveTopKArgs(BaseModel):
    query: str = Field(..., description="The claim/question to check against the PDF index.")
    k: int = Field(5, ge=1, le=20, description="Number of top relevant chunks to retrieve.")


RETRIEVE_TOP_K_TOOL = StructuredTool.from_function(
    func=retrieve_top_k,
    name="retrieve_top_k",
    description="Retrieve top-k most relevant PDF text chunks (with metadata) using vector similarity search.",
    args_schema=RetrieveTopKArgs,
)




from retriever import load_index_and_metadata


class LoadIndexArgs(BaseModel):
    """No input needed; we just load the current persisted index + metadata."""
    pass


def tool_load_index_and_metadata():
    """
    Loads the persisted FAISS index + metadata from disk.
    Returns only JSON-serializable info so it can be safely logged/displayed.
    """
    index, meta = load_index_and_metadata()

    # Don't return the raw FAISS index object (not JSON-serializable).
    return {
        "index_type": type(index).__name__,
        "meta_keys": list(meta.keys()),
        "num_texts": len(meta.get("texts", [])),
        "example_sources": (meta.get("sources", [])[:3] if isinstance(meta.get("sources", []), list) else None),
    }


LOAD_INDEX_AND_METADATA_TOOL = StructuredTool.from_function(
    func=tool_load_index_and_metadata,
    name="load_index_and_metadata",
    description="Load the persisted FAISS index and its metadata (audit/debug). Returns only summary info.",
    args_schema=LoadIndexArgs,
)



from build_index import embed_texts
from openai import OpenAI


class EmbedTextsArgs(BaseModel):
    texts: list[str] = Field(..., description="List of texts (e.g., chunks) to embed.")


def tool_embed_texts(texts: list[str]):
    """
    Create embeddings for a list of texts using the same embedding logic used in indexing.
    Returns a list of vectors (list of floats).
    """
    client = OpenAI()
    return embed_texts(client=client, texts=texts)


EMBED_TEXTS_TOOL = StructuredTool.from_function(
    func=tool_embed_texts,
    name="embed_texts",
    description="Generate embeddings for a list of texts (raw text -> vector).",
    args_schema=EmbedTextsArgs,
)
