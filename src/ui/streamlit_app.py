"""
Streamlit UI entrypoint.

This file currently serves two purposes:
1) Demo of ValueSpec + refusal-driven deterministic tools (your exergy safety story).
2) Academic PDF claim-checker RAG demo.

Important design rule:
- UI must NOT do inline physics math.
- UI calls deterministic tools from src/tools/.
"""

from __future__ import annotations

# ----------------------------
# PATH FIX FOR STREAMLIT
# ----------------------------
# Streamlit sometimes runs scripts with a working directory that breaks "import src....".
# We fix this by adding the REPO ROOT (the folder that contains /src) to sys.path.
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]  # .../seasonal-energy-storage-exergy-copilot
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ----------------------------
# STANDARD LIBRARY IMPORTS
# ----------------------------
import os
import re
import tempfile

import streamlit as st
from dotenv import load_dotenv

# Ensure .env variables are available locally
load_dotenv(override=True)

# ----------------------------
# PROJECT IMPORTS (ALWAYS use src.* only)
# ----------------------------
from src.core.values import (
    ValueSpec,
    Citation,
    assumption_value,
    external_value,
    evidence_value,
)
from src.core.refusal import RefusalError
from src.core.guardrails import refuse_if_delivery_boundary_missing
from src.core.science_config import FUNCTIONAL_UNIT
from src.core.validate_values import require_source

from src.tools.exergy_core import thermal_exergy_of_heat
from src.tools.exergy_checks import exergy_destruction_balance

# NOTE:
# Do NOT import tools.equation_tool (without src.). It will break.
# If/when you need equation extraction, import it as:
# from src.tools.equation_tool import retrieve_equations


# ----------------------------
# SESSION STATE INIT
# ----------------------------
if "session_evidence" not in st.session_state:
    st.session_state.session_evidence = []


# ----------------------------
# CONSTANTS
# ----------------------------
FALLBACK_MSG = "This information is not available in the document."


# ----------------------------
# SMALL HELPERS (PURE UI UTILITIES)
# ----------------------------
def get_openai_api_key() -> str | None:
    """
    Return API key for Streamlit Cloud or local .env.
    """
    # 1) Streamlit Cloud Secrets
    try:
        key = st.secrets.get("OPENAI_API_KEY")
        if key:
            return str(key).strip()
    except Exception:
        pass

    # 2) Environment variable (.env loads into env)
    key = os.getenv("OPENAI_API_KEY")
    return key.strip() if key else None


def clean_text(t: str) -> str:
    """
    Light text normalization for academic PDFs.
    This is deterministic (no LLM).
    """
    if not t:
        return ""
    t = t.replace("\r", "\n")
    t = re.sub(r"[ \t]+", " ", t)            # collapse spaces
    t = re.sub(r"\n{3,}", "\n\n", t)         # collapse huge newlines
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)   # fix hyphen line breaks
    t = re.sub(r"(?<!\n)\n(?!\n)", " ", t)   # join single line breaks
    return t.strip()


def extract_relevant_sentences(chunk_text: str, query: str, max_sentences: int = 3) -> list[str]:
    """
    Deterministically extract up to N sentences from a chunk that best match the query.
    No LLM. Low risk. Great for UI evidence.
    """
    if not chunk_text:
        return []

    text = chunk_text.replace("\n", " ").strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    q = query.lower()
    q_tokens = [t for t in re.findall(r"[a-zA-Z0-9]+", q) if len(t) >= 4]
    if not q_tokens:
        return sentences[:max_sentences]

    scored: list[tuple[int, str]] = []
    for s in sentences:
        sl = s.lower()
        score = sum(1 for tok in q_tokens if tok in sl)
        if score > 0:
            scored.append((score, s))

    scored.sort(key=lambda x: x[0], reverse=True)
    picked = [s for _, s in scored[:max_sentences]]

    return picked if picked else sentences[:max_sentences]


def show_value(label: str, v: ValueSpec) -> None:
    """
    UI renderer for ValueSpec.

    Important:
    - require_source() ensures the ValueSpec is properly tagged (Evidence/Computed/etc.)
    - this enforces your thesis-grade provenance rule at display time.
    """
    require_source(v)

    st.write(f"**{label}**")
    st.write(f"- value: {v.value} {v.unit}")
    st.write(f"- source: {v.source_type.value}")

    if v.citation:
        st.write(f"- citation: {v.citation.pdf_name}, page {v.citation.page}")
        if v.citation.short_quote:
            st.write(f"- quote: {v.citation.short_quote}")

    if v.meta:
        st.write(f"- meta: {v.meta}")


def run_with_refusal(fn, *args, **kwargs):
    """
    Run deterministic functions that may refuse.
    Returns (result, None) or (None, RefusalError).
    """
    try:
        return fn(*args, **kwargs), None
    except RefusalError as e:
        return None, e


def show_refusal(e: RefusalError) -> None:
    """
    Render refusal info in a user-friendly way.
    """
    st.error(e.user_message)
    st.caption(f"Why: {e.why}")

    if e.missing:
        st.caption("Missing / required:")
        for m in e.missing:
            st.write(f"- {m}")

    if e.details:
        st.caption("Details:")
        st.json(e.details)


# ----------------------------
# RUNTIME INDEX BUILDER (RAG)
# ----------------------------
def build_runtime_index_from_paths(pdf_paths: list[str]) -> None:
    """
    Build FAISS index in-memory from uploaded PDF paths.
    Stores index + texts + metadatas in st.session_state.

    This function is UI-support code. It is NOT physics.
    """
    from langchain_community.document_loaders import PyMuPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    import faiss
    import numpy as np
    from openai import OpenAI

    if not os.getenv("OPENAI_API_KEY"):
        st.error("OPENAI_API_KEY is missing.")
        st.stop()

    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 150
    EMBED_MODEL = "text-embedding-3-small"

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )

    docs = []
    for p in pdf_paths:
        loader = PyMuPDFLoader(p)
        page_docs = loader.load()
        for d in page_docs:
            d.metadata["source_file"] = Path(p).name
        docs.extend(page_docs)

    for d in docs:
        d.page_content = clean_text(d.page_content)

    chunks = splitter.split_documents(docs)

    texts = []
    metadatas = []
    for c in chunks:
        t = (c.page_content or "").strip()
        if not t:
            continue
        texts.append(t)
        metadatas.append({
            "source_file": c.metadata.get("source_file"),
            "page": c.metadata.get("page"),
        })

    client = OpenAI()
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    vectors = np.array([item.embedding for item in resp.data], dtype="float32")

    dim = vectors.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(vectors)

    st.session_state.runtime_index = index
    st.session_state.runtime_texts = texts
    st.session_state.runtime_metadatas = metadatas
    st.session_state.runtime_index_ready = True


def format_source_title(filename: str, page: int) -> str:
    """
    Convert PDF filename into a clean, academic-style source title.
    Example:
    Metal_Hydride_Energy_Technology_Overview.pdf
    → Metal Hydride Energy Technology Overview, p. 3
    """
    if not filename:
        return f"Document, p. {page}"

    name = filename.replace(".pdf", "")
    name = name.replace("_", " ").strip()
    name = " ".join(w.capitalize() for w in name.split())
    return f"{name}, p. {page}"


def runtime_retrieve_top_k(query: str, k: int = 5):
    """
    Retrieve from the in-memory FAISS index built from uploaded PDFs.
    Returns list of dicts: rank, distance, text, source_file, page.
    """
    import numpy as np
    from openai import OpenAI

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing.")

    if not st.session_state.get("runtime_index_ready", False):
        return []

    index = st.session_state.runtime_index
    texts = st.session_state.runtime_texts
    metadatas = st.session_state.runtime_metadatas

    client = OpenAI()
    emb = client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    )
    qv = np.array(emb.data[0].embedding, dtype="float32").reshape(1, -1)

    distances, indices = index.search(qv, k)

    results = []
    for rank, idx in enumerate(indices[0], start=1):
        if idx < 0:
            continue
        md = metadatas[idx]
        results.append({
            "rank": rank,
            "distance": float(distances[0][rank - 1]),
            "text": texts[idx],
            "source_file": md.get("source_file"),
            "page": md.get("page"),
        })
    return results


def rewrite_for_retrieval(user_question: str) -> str:
    """
    Turn a messy user request (any language, any instructions)
    into a short search query for retrieval ONLY.
    """
    from openai import OpenAI

    client = OpenAI()
    msg = [
        {"role": "system", "content":
         "You are a query rewriter. Your job is to extract ONLY what to search for in the document. "
         "Remove formatting/instruction text (e.g., 'quote exactly', 'copy paste', 'do not paraphrase'). "
         "Return a short search query (max 15 words). Do NOT answer the question."},
        {"role": "user", "content": user_question}
    ]

    r = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=msg,
        temperature=0.0,
    )
    q = r.choices[0].message.content.strip()
    return q if q else user_question


def runtime_grounded_answer(question: str, top_k: int = 5):
    """
    Grounded answer using ONLY uploaded PDFs (runtime index).
    If not relevant -> refuse with FALLBACK_MSG and do NOT call LLM.
    """
    from openai import OpenAI

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing.")

    retrieval_query = rewrite_for_retrieval(question)
    retrieved = runtime_retrieve_top_k(retrieval_query, k=top_k)

    RELEVANCE_DISTANCE_THRESHOLD = 1.6
    distances = [r.get("distance", 9999.0) for r in retrieved]
    best_distance = min(distances) if distances else 9999.0

    if best_distance > RELEVANCE_DISTANCE_THRESHOLD:
        return {
            "question": question,
            "answer": FALLBACK_MSG,
            "citations": [],
            "llm_called": False,
            "retrieved_chunks": 0,
            "retrieved": retrieved,
        }

    context_parts = []
    citations = []
    for r in retrieved:
        text = (r.get("text") or "").strip()
        if not text:
            continue
        sf = r.get("source_file")
        pg = r.get("page")
        context_parts.append(f"[SOURCE: {sf} | page: {pg}]\n{text}\n")
        citations.append({"source_file": sf, "page": pg})

    # Deduplicate citations
    seen = set()
    deduped = []
    for c in citations:
        key = (c.get("source_file"), c.get("page"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(c)

    system_prompt = (
        "You are a strictly grounded academic assistant.\n"
        "You MUST answer using ONLY the provided CONTEXT.\n"
        "If the CONTEXT does not contain the needed information, reply exactly:\n"
        f"\"{FALLBACK_MSG}\".\n"
        "Do NOT use outside knowledge. Do NOT guess. Do NOT hallucinate.\n"
    )

    context_block = "\n---\n".join(context_parts)

    user_prompt = (
        f"QUESTION:\n{question}\n\n"
        f"CONTEXT:\n{context_block}\n\n"
        "INSTRUCTIONS:\n"
        "Answer the QUESTION using ONLY the CONTEXT.\n"
    )

    client = OpenAI()
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
    )

    answer_text = resp.choices[0].message.content.strip()

    return {
        "question": question,
        "answer": answer_text,
        "citations": deduped,
        "llm_called": True,
        "retrieved_chunks": len(retrieved),
        "retrieved": retrieved,
    }


# ----------------------------
# STREAMLIT UI START
# ----------------------------
st.set_page_config(page_title="Academic PDF Claim-Checker RAG", layout="centered")

st.title("Academic PDF Claim-Checker (Strict, No Hallucinations)")
st.caption(f"Functional unit (frozen): {FUNCTIONAL_UNIT.description}")

st.markdown(
    """
    **Academic, document-grounded decision-support tool**  
    Domain: Any academic PDFs (papers, reports, theses)
    """
)

# ----------------------------
# DEMO: VALUE TAGGING + TOOL SAFETY
# ----------------------------
st.header("TASK 0.3 Demo — all numbers are source-tagged")

v_assumption = assumption_value(293.15, "K", meta={"note": "User provided T0"})

v_external = external_value(
    120.0,
    "EUR/MWh",
    meta={"source": "Demo placeholder", "time_range": "2022 (annual avg, DE)"},
)

Q_demo = external_value(
    1_000_000.0,
    "J",
    meta={"source": "Demo placeholder", "time_range": "single-run"},
)

Tb_demo = assumption_value(353.15, "K", meta={"note": "Assumed boundary temperature"})
T0_demo = assumption_value(293.15, "K", meta={"note": "Assumed reference environment temperature"})

# IMPORTANT: UI does not compute inline. It calls deterministic tools.
v_computed = thermal_exergy_of_heat(Q=Q_demo, Tb_K=Tb_demo, T0_K=T0_demo)

v_evidence = evidence_value(
    0.72,
    "-",
    citation=Citation(
        pdf_name="ExamplePaper.pdf",
        page=5,
        chunk_id="chunk_12",
        short_quote="Electrolyzer efficiency is 0.72",
    ),
)

show_value("Assumption: T0", v_assumption)
show_value("External: Electricity price", v_external)
show_value("Computed: Exergy of heat", v_computed)
show_value("Evidence: Electrolyzer efficiency", v_evidence)

# ----------------------------
# DEMO: REFUSE-TO-COMPUTE
# ----------------------------
st.subheader("TASK 0.4 — Refuse-to-compute demo")

# 0.4.4 Delivery boundary missing
delivery_boundary = None
_, err = run_with_refusal(refuse_if_delivery_boundary_missing, delivery_boundary)
if err:
    st.markdown("**0.4.4 Delivery boundary missing**")
    show_refusal(err)

# 0.4.1 T0 missing
st.markdown("**0.4.1 T0 missing**")
Tb = assumption_value(343.15, "K", meta={"note": "DH boundary temperature"})
Qj = external_value(5.0e9, "J", meta={"source": "Demo external input", "time_range": "2024"})
_, err = run_with_refusal(thermal_exergy_of_heat, Qj, Tb, None)
if err:
    show_refusal(err)

# 0.4.2 Unit ambiguous: MWh/kWh/Wh without meta.energy_kind
st.markdown("**0.4.2 Unit ambiguous: MWh thermal vs electric**")
T0 = assumption_value(288.15, "K", meta={"note": "Reference temperature"})
Q_mwh_amb = external_value(1.0, "MWh", meta={"source": "Demo external input", "time_range": "2024"})
_, err = run_with_refusal(thermal_exergy_of_heat, Q_mwh_amb, Tb, T0)
if err:
    show_refusal(err)

# 0.4.3 Negative exergy destruction
st.markdown("**0.4.3 Negative exergy destruction**")
Ex_in = external_value(100.0, "J", meta={"source": "Demo", "time_range": "2024"})
Ex_out = external_value(120.0, "J", meta={"source": "Demo", "time_range": "2024"})
_, err = run_with_refusal(exergy_destruction_balance, Ex_in, Ex_out)
if err:
    show_refusal(err)

# ----------------------------
# UPLOAD PDFs
# ----------------------------
st.subheader("1) Upload PDFs")

uploaded_files = st.file_uploader(
    "Upload one or more PDF files",
    type=["pdf"],
    accept_multiple_files=True
)

# Session state init for uploads
if "upload_dir" not in st.session_state:
    st.session_state.upload_dir = Path(tempfile.mkdtemp(prefix="rag_uploads_"))

if "uploaded_pdf_paths" not in st.session_state:
    st.session_state.uploaded_pdf_paths = []

if "runtime_index_ready" not in st.session_state:
    st.session_state.runtime_index_ready = False

if "upload_signature" not in st.session_state:
    st.session_state.upload_signature = None

# Save PDFs + Auto index only when files change
if uploaded_files:
    saved_paths = []
    for uf in uploaded_files:
        save_path = st.session_state.upload_dir / uf.name
        save_path.write_bytes(uf.getbuffer())
        saved_paths.append(str(save_path))

    st.session_state.uploaded_pdf_paths = saved_paths

    current_signature = tuple(sorted((uf.name, uf.size) for uf in uploaded_files))

    if st.session_state.upload_signature != current_signature:
        st.session_state.runtime_index_ready = False
        with st.spinner("Preparing documents for claim checking..."):
            build_runtime_index_from_paths(saved_paths)
        st.session_state.upload_signature = current_signature
else:
    st.session_state.uploaded_pdf_paths = []
    st.session_state.runtime_index_ready = False
    st.session_state.upload_signature = None
    st.info("No PDFs uploaded yet.")

# ----------------------------
# QUESTION UI
# ----------------------------
question = st.text_area(
    "Enter your question:",
    placeholder="Example: Does the paper explicitly claim that X causes Y? If yes, quote exact sentences and cite page."
)

submit_clicked = st.button("Run", type="primary")
if not submit_clicked:
    st.stop()

st.caption("Tip: Upload PDF first. Then type your claim/question. Then click Run.")

if not st.session_state.uploaded_pdf_paths:
    st.warning("Please upload at least one PDF.")
    st.stop()

if not question.strip():
    st.warning("Please type a claim/question first.")
    st.stop()

with st.spinner("Checking claim against uploaded documents..."):
    result = runtime_grounded_answer(question, top_k=5)
    retrieved = result.get("retrieved", [])

answer_text = (result.get("answer") or "").strip()
citations_list = result.get("citations") or []
is_found = (answer_text != FALLBACK_MSG) and (len(citations_list) > 0)

# ----------------------------
# ANSWER UI
# ----------------------------
st.subheader("Answer")
st.write(answer_text)

# ----------------------------
# TOOL OUTPUT UI
# ----------------------------
st.subheader("🔧 Tool Output: Retrieved Chunks")

with st.expander("Show retrieved document chunks (retrieve_top_k output)"):
    if not retrieved:
        st.write("No chunks retrieved.")
    else:
        for r in retrieved:
            rank = r.get("rank")
            dist = r.get("distance")
            sf = r.get("source_file")
            pg = r.get("page")
            human_page = (pg + 1) if isinstance(pg, int) else pg

            st.markdown(
                f"""
**Rank:** {rank}  
**Distance:** {dist:.4f}  
**Source file:** {sf}  
**Page:** {human_page} *(loader page index: {pg})*
"""
            )

            preview = (r.get("text") or "").strip().replace("\n", " ")
            st.code(preview[:700] + ("..." if len(preview) > 700 else ""), language="text")
            st.markdown("---")

# ----------------------------
# SOURCES UI
# ----------------------------
st.subheader("Sources")

if not citations_list:
    st.write("No sources available.")
else:
    grouped = {}
    for r in retrieved:
        sf = r.get("source_file")
        pg = r.get("page")
        key = (sf, pg)
        grouped.setdefault(key, []).append(r)

    global_best = min([r.get("distance", 9999.0) for r in retrieved], default=9999.0)
    max_allowed = global_best + 0.03

    evidence_by_key = {}
    for key, chunks_list in grouped.items():
        key_best = min([r.get("distance", 9999.0) for r in chunks_list], default=9999.0)
        if key_best > max_allowed:
            continue

        all_sentences = []
        for r in chunks_list:
            sentences = extract_relevant_sentences(r.get("text", ""), question, max_sentences=3)
            if sentences:
                all_sentences.extend(sentences)

        if all_sentences:
            unique = []
            seen_s = set()
            for s in all_sentences:
                if s in seen_s:
                    continue
                seen_s.add(s)
                unique.append(s)
            evidence_by_key[key] = unique

    seen = set()
    for c in citations_list:
        sf = c.get("source_file")
        pg = c.get("page")
        key = (sf, pg)
        if key in seen:
            continue
        seen.add(key)

        if key not in evidence_by_key:
            continue

        source_title = format_source_title(sf, pg)
        with st.expander(source_title):
            st.markdown("**Evidence sentences**")
            for s in evidence_by_key[key]:
                st.write(f"• {s}")
