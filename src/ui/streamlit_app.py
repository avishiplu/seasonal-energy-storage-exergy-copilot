# src/streamlit_app.py

import sys
sys.path.append("src")

import streamlit as st
from pathlib import Path
import tempfile
import os
import re

from dotenv import load_dotenv

load_dotenv(override=True)

from core.values import (
    ValueSpec,
    SourceType,
    Citation,
    assumption_value,
    external_value,
    evidence_value
)


from core.refusal import RefusalError
from core.guardrails import refuse_if_delivery_boundary_missing
from tools.exergy_checks import exergy_destruction_balance
from core.science_config import FUNCTIONAL_UNIT



def get_openai_api_key() -> str | None:
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



if "session_evidence" not in st.session_state:
    st.session_state.session_evidence = []


FALLBACK_MSG = "This information is not available in the document."


def clean_text(t: str) -> str:
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

    # crude sentence split (good enough for academic prose)
    text = chunk_text.replace("\n", " ").strip()
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    # keyword scoring: keep it simple and robust
    q = query.lower()
    q_tokens = [t for t in re.findall(r"[a-zA-Z0-9]+", q) if len(t) >= 4]
    if not q_tokens:
        return sentences[:max_sentences]

    scored = []
    for s in sentences:
        sl = s.lower()
        score = sum(1 for tok in q_tokens if tok in sl)
        if score > 0:
            scored.append((score, s))

    scored.sort(key=lambda x: x[0], reverse=True)
    picked = [s for _, s in scored[:max_sentences]]

    # fallback: if nothing matched, return first sentence(s)
    return picked if picked else sentences[:max_sentences]


def build_runtime_index_from_paths(pdf_paths: list[str]) -> None:
    """
    Build FAISS index in-memory from uploaded PDF paths.
    Stores index + texts + metadatas in st.session_state.
    This is INTERNAL. User should not see "index" concepts.
    """
    from langchain_community.document_loaders import PyMuPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    import faiss
    import numpy as np
    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv()
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

    # Load all pages
    docs = []
    for p in pdf_paths:
        loader = PyMuPDFLoader(p)
        page_docs = loader.load()
        for d in page_docs:
            d.metadata["source_file"] = Path(p).name
        docs.extend(page_docs)

    # Light cleanup
    for d in docs:
        d.page_content = clean_text(d.page_content)

    # Chunk
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


    # Embed
    client = OpenAI()
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    vectors = np.array([item.embedding for item in resp.data], dtype="float32")

    # Build FAISS
    dim = vectors.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(vectors)

    # Save to session
    st.session_state.runtime_index = index
    st.session_state.runtime_texts = texts
    st.session_state.runtime_metadatas = metadatas
    st.session_state.runtime_index_ready = True


# ----------------------------
# UI
# ----------------------------
st.set_page_config(
    page_title="Academic PDF Claim-Checker RAG",
    layout="centered"
)

def show_value(label: str, v: ValueSpec):
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
    try:
        return fn(*args, **kwargs), None
    except RefusalError as e:
        return None, e

def show_refusal(e: RefusalError):
    st.error(e.user_message)
    st.caption(f"Why: {e.why}")

    if e.missing:
        st.caption("Missing / required:")
        for m in e.missing:
            st.write(f"- {m}")

    if e.details:
        st.caption("Details:")
        st.json(e.details)


st.title("Academic PDF Claim-Checker (Strict, No Hallucinations)")
st.caption(f"Functional unit (frozen): {FUNCTIONAL_UNIT.description}")
st.markdown(
    """
    **Academic, document-grounded decision-support tool**  
    Domain: Any academic PDFs (papers, reports, theses)
    """
)


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




st.subheader("TASK 0.4 — Refuse-to-compute demo")

# --- 0.4.4 Delivery boundary missing ---
delivery_boundary = None
_, err = run_with_refusal(refuse_if_delivery_boundary_missing, delivery_boundary)
if err:
    st.markdown("**0.4.4 Delivery boundary missing**")
    show_refusal(err)

# --- 0.4.1 T0 missing ---
st.markdown("**0.4.1 T0 missing**")
Tb = assumption_value(343.15, "K", meta={"note": "DH boundary temperature"})
Qj = external_value(5.0e9, "J", meta={"source": "Demo external input", "time_range": "2024"})
Ex, err = run_with_refusal(thermal_exergy_of_heat, Qj, Tb, None)
if err:
    show_refusal(err)

# --- 0.4.2 Unit ambiguous: MWh/kWh/Wh without meta.energy_kind ---
st.markdown("**0.4.2 Unit ambiguous: MWh thermal vs electric**")
T0 = assumption_value(288.15, "K", meta={"note": "Reference temperature"})
Q_mwh_amb = external_value(1.0, "MWh", meta={"source": "Demo external input", "time_range": "2024"})
Ex, err = run_with_refusal(thermal_exergy_of_heat, Q_mwh_amb, Tb, T0)
if err:
    show_refusal(err)

# --- 0.4.3 Negative exergy destruction ---
st.markdown("**0.4.3 Negative exergy destruction**")
Ex_in = external_value(100.0, "J", meta={"source": "Demo", "time_range": "2024"})
Ex_out = external_value(120.0, "J", meta={"source": "Demo", "time_range": "2024"})  # out > in -> negative
Ex_dest, err = run_with_refusal(exergy_destruction_balance, Ex_in, Ex_out)
if err:
    show_refusal(err)




st.subheader("1) Upload PDFs")

uploaded_files = st.file_uploader(
    "Upload one or more PDF files",
    type=["pdf"],
    accept_multiple_files=True
)


# Session state init
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
    # Save uploaded PDFs to disk
    saved_paths = []
    for uf in uploaded_files:
        save_path = st.session_state.upload_dir / uf.name
        save_path.write_bytes(uf.getbuffer())
        saved_paths.append(str(save_path))

    st.session_state.uploaded_pdf_paths = saved_paths


    # Create signature to avoid rebuilding on every rerun
    current_signature = tuple(sorted((uf.name, uf.size) for uf in uploaded_files))

    # If different PDFs than before -> rebuild automatically
    if st.session_state.upload_signature != current_signature:
        st.session_state.runtime_index_ready = False
        with st.spinner("Preparing documents for claim checking..."):
            build_runtime_index_from_paths(saved_paths)

        # Save signature after successful build
        st.session_state.upload_signature = current_signature

else:
    # No PDFs uploaded
    st.session_state.uploaded_pdf_paths = []
    st.session_state.runtime_index_ready = False
    st.session_state.upload_signature = None
    st.info("No PDFs uploaded yet.")


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





# -----------------------------
# Runtime RAG helpers
# -----------------------------
def runtime_retrieve_top_k(query: str, k: int = 5):
    """
    Retrieve from the in-memory FAISS index built from uploaded PDFs.
    Returns list of dicts: rank, distance, text, source_file, page.
    """
    import numpy as np
    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv()
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
    from dotenv import load_dotenv
    from openai import OpenAI
    import os

    load_dotenv()
    client = OpenAI()

    # Very short, strict prompt: ONLY make a search query, no answering
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
    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing.")

    retrieval_query = rewrite_for_retrieval(question)
    retrieved = runtime_retrieve_top_k(retrieval_query, k=top_k)

    # ----------------------------
    # Relevance gate + GENERIC keyword fallback
    # (no hard-coded equation names)
    # ----------------------------
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



    # Build context + citations
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

st.subheader("2) Choose mode")

mode = "Claim Check (Strict)"


# ----------------------------
# Question UI
# ----------------------------
question = st.text_area(
    "Enter your question:",
    placeholder="Example: Does the paper explicitly claim that X causes Y? If yes, quote the exact sentence(s) and cite page."
)

submit_clicked = st.button("Run", type="primary")
if not submit_clicked:
    st.stop()


st.caption("Tip: Upload PDF first. Then type your claim/question. Then click Run.")

# ----------------------------
# Claim Check ALWAYS
# ----------------------------
if not st.session_state.uploaded_pdf_paths:
    st.warning("Please upload at least one PDF.")
    st.stop()

if not question.strip():
    st.warning("Please type a claim/question first.")
    st.stop()

with st.spinner("Checking claim against uploaded documents..."):
    result = runtime_grounded_answer(question, top_k=5)
    retrieved = result.get("retrieved", [])


# ----------------------------
# Determine FOUND / NOT_FOUND (ONLY ONCE)
# ----------------------------
answer_text = (result.get("answer") or "").strip()
citations_list = result.get("citations") or []
is_found = (answer_text != FALLBACK_MSG) and (len(citations_list) > 0)

# ----------------------------
# Auto Equation Extraction (Option 2) - ONLY WHEN FOUND
# ----------------------------
# Auto Equation Extraction (Option 2) - ONLY WHEN FOUND
if is_found:
    ql = question.lower()
    wants_equation = any(
        k in ql
        for k in ["equation", "eq.", "van’t hoff", "van't hoff", "ln", "delta", "Δ", "peqt", "peq", "pref"]
    )

    if wants_equation:
        from tools.equation_tool import retrieve_equations


        st.subheader("Extracted equation(s)")

        with st.spinner("Extracting equation(s) in reusable format..."):
            eq_result = eq_result = retrieve_equations(
                pdf_paths=st.session_state.uploaded_pdf_paths,
                query=question,
                max_hits=10,
            )

        hits = eq_result.get("hits", [])
        if not hits:
            st.warning(
                "Claim is FOUND, but text-based equation extraction returned no clean equation objects. "
                "Next step is adding OCR-crop fallback for perfect extraction."
            )
        else:
            for i, h in enumerate(hits, start=1):
                title = f'{h["source_file"]}, p. {h["page"] + 1} (Equation #{i})'
                with st.expander(title):
                    st.markdown("**Evidence lines (from PDF text):**")
                    for line in h.get("evidence_lines", []):
                        st.write(f"• {line}")

                    st.markdown("**LaTeX (UI / paper):**")
                    st.code(h.get("latex", ""), language="latex")

                    st.markdown("**Machine expression (for computation):**")
                    st.code(h.get("machine_expr", h.get("ascii", "")), language="text")

                    st.markdown("**JSON (structured for agents):**")
                    st.json(h.get("json", {}))

# ----------------------------
# Session Evidence Memory (use the SAME is_found)
# ----------------------------
if is_found:
    first = citations_list[0]
    pdf_name = first.get("source_file")
    page_no = first.get("page")
else:
    pdf_name = None
    page_no = None

st.session_state.session_evidence.append({
    "status": "FOUND" if is_found else "NOT_FOUND",
    "claim": question[:60] + ("…" if len(question) > 60 else ""),
    "pdf": pdf_name,
    "page": page_no
})

# ----------------------------
# Answer UI
# ----------------------------
st.subheader("Answer")
st.write(answer_text)

# ----------------------------
# Tool Output UI (SHOW retrieved chunks)
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

            # Human-friendly page (most PDFs show pages starting from 1)
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
# Sources UI (existing logic, keep)
# ----------------------------
retrieved = result.get("retrieved", [])
citations = citations_list

st.subheader("Sources")

if not citations:
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
            sentences = extract_relevant_sentences(
                r.get("text", ""),
                question,
                max_sentences=3
            )
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
    for c in citations:
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

# ----------------------------
# Verified Evidence Table UI (existing logic, keep)
# ----------------------------
st.subheader("📚 Verified Evidence This Session")

if not st.session_state.session_evidence:
    st.write("No claims checked yet in this session.")
else:
    header_cols = st.columns([1, 4, 3, 1, 2])
    header_cols[0].markdown("**Status**")
    header_cols[1].markdown("**Claim**")
    header_cols[2].markdown("**PDF**")
    header_cols[3].markdown("**Page**")
    header_cols[4].markdown("**Action**")

    for row in st.session_state.session_evidence:
        cols = st.columns([1, 4, 3, 1, 2])

        if row["status"] == "FOUND":
            cols[0].write("✅")
            cols[1].write(row["claim"])
            cols[2].write(row["pdf"])
            cols[3].write(row["page"])
            cols[4].code(f'{row["pdf"]}, p. {row["page"]}', language="text")
        else:
            cols[0].write("❌")
            cols[1].write(row["claim"])
            cols[2].write("—")
            cols[3].write("—")
            cols[4].write("Not found")
