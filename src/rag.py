"""
rag.py

Task 9 — RAG Prompt + Answer Flow (Grounded Answer Synthesis)

What this module does:
- Calls the retriever (Task 8) to get top-k relevant chunks with metadata
- Builds a strict, anti-hallucination prompt using ONLY retrieved context
- Asks the LLM to synthesize an answer grounded in the provided context
- Returns answer + citations (source_file, page)

What this module does NOT do:
- No re-embedding, no FAISS rebuild (Task 7)
- No UI wiring (Streamlit/app.py comes later)
"""

from __future__ import annotations

import os
from typing import List, Dict, Any, Tuple

from dotenv import load_dotenv
from openai import OpenAI

from lc_tools import RETRIEVE_TOP_K_TOOL

TOP_K = 5

# Relevance threshold for retrieval (lower = stricter)
RELEVANCE_DISTANCE_THRESHOLD = 0.75

# Canonical fallback (must match Streamlit + CLI)
FALLBACK_MSG = "This information is not available in the document."



# Embedding model is handled in retriever.py
# Here we only select the chat model for synthesis
CHAT_MODEL = "gpt-4.1-mini"  # stable + cost-effective for synthesis


def build_context_block(retrieved: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Convert retrieved chunks into a single context string for the prompt.
    Also returns a cleaned citations list for downstream use.
    """
    context_parts: List[str] = []
    citations: List[Dict[str, Any]] = []

    for r in retrieved:
        source_file = r.get("source_file")
        page = r.get("page")
        text = (r.get("text") or "").strip()

        # Keep only non-empty chunks
        if not text:
            continue

        context_parts.append(
            f"[SOURCE: {source_file} | page: {page}]\n{text}\n"
        )
        citations.append({"source_file": source_file, "page": page})

    return "\n---\n".join(context_parts), citations

def dedupe_citations(citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate citations while preserving order.
    Duplicates are defined by (source_file, page).
    """
    seen = set()
    out: List[Dict[str, Any]] = []
    for c in citations:
        key = (c.get("source_file"), c.get("page"))
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def strip_model_sources(answer: str) -> str:
    """
    Remove any model-generated 'Sources:' section from the answer text.
    We control sources separately to keep output consistent and verifiable.
    """
    marker = "(Sources:"
    if marker in answer:
        answer = answer.split(marker, 1)[0].rstrip()
    return answer


def grounded_answer(question: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Generate a grounded answer using RAG.

    Flow:
    1) Retrieve top-k chunks
    2) Check semantic relevance (distance-based gate)
    3) If not relevant -> return fallback (not in document)
    4) If relevant -> build context, call LLM
    5) Clean answer and return with citations
    """

    # --------------------------------------------------
    # Environment check
    # --------------------------------------------------
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing. Put it in .env and retry.")

    # --------------------------------------------------
    # Step 1: Retrieve candidate chunks
    # --------------------------------------------------
    retrieved = RETRIEVE_TOP_K_TOOL.invoke({"query": question, "k": TOP_K})


    # --------------------------------------------------
    # Step 2: Relevance gate (VERY IMPORTANT)
    # If retrieved chunks are not semantically close enough,
    # we stop here and DO NOT call the LLM.
    # --------------------------------------------------
    distances = [r.get("distance", 1.0) for r in retrieved]
    best_distance = min(distances) if distances else 1.0

    if best_distance > RELEVANCE_DISTANCE_THRESHOLD:
        return {
            "question": question,
            "answer": FALLBACK_MSG,
            "citations": [],
            "llm_called": False,
            "retrieved_chunks": 0,
            "best_distance": best_distance,
        }


    # --------------------------------------------------
    # Step 3: Build context and clean citations
    # (Only reached if relevance gate passed)
    # --------------------------------------------------
    context, citations = build_context_block(retrieved)
    citations = dedupe_citations(citations)

    # --------------------------------------------------
    # Step 4: Build strict RAG prompt
    # --------------------------------------------------
    system_prompt = (
        "You are a strictly grounded academic assistant.\n"
        "You MUST answer using ONLY the provided CONTEXT.\n"
        "If the CONTEXT does not contain the needed information, reply exactly:\n"
        "\"{FALLBACK_MSG}\".\n"
        "Do NOT use outside knowledge. Do NOT guess. Do NOT hallucinate.\n"
    )

    user_prompt = (
        f"QUESTION:\n{question}\n\n"
        f"CONTEXT:\n{context}\n\n"
        "INSTRUCTIONS:\n"
        "Answer the QUESTION using ONLY the CONTEXT.\n"
    )

    # --------------------------------------------------
    # Step 5: Call LLM (answer synthesis only)
    # --------------------------------------------------
    client = OpenAI()
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
    )

    # --------------------------------------------------
    # Step 6: Clean model output and return
    # --------------------------------------------------
    answer_text = resp.choices[0].message.content.strip()
    answer_text = strip_model_sources(answer_text)

    return {
        "question": question,
        "answer": answer_text,
        "citations": citations,
        "llm_called": True,
        "retrieved_chunks": len(retrieved),
    }


def main() -> None:
    # Simple CLI test
    q = "List the key advantages and disadvantages of metal hydride materials (e.g., LaNi5, Mg2Ni, TiFe) mentioned in the documents."
    result = grounded_answer(q, top_k=5)

    print("\n--- RAG Answer ---")
    print("Q:", result["question"])
    print("\nA:\n", result["answer"])

    print("\n--- Sources ---")
    for c in result["citations"]:
        print(f"- {c['source_file']} | page: {c['page']}")


if __name__ == "__main__":
    main()
