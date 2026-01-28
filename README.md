# Academic PDF Claim Checker & Equation Extractor

Sprint 2 — AI Engineering

---

## Project Overview

This project is developed as part of **AI Engineering – Sprint 2**.

The application is a **strict academic PDF claim checker** that verifies whether a claim or equation is **explicitly present in an academic paper** and extracts it in structured formats.

This is **not** a generic “chat with PDF” system.

The core focus is:

* Retrieval-Augmented Generation (RAG)
* Tool-based document retrieval
* Hallucination-free, evidence-based answers

---

## Assignment Scope (Sprint 2)

Sprint 2 focuses on:

* LangChain fundamentals
* Retrieval-Augmented Generation (RAG)
* Tool / function usage
* Building a practical AI application with Streamlit

**Agents are intentionally NOT used**, as they are introduced in Sprint 3.

---

## Core Design Principle

The system enforces strict separation of responsibilities:

Verification ≠ Extraction ≠ Computation

* Verification: checks if information explicitly exists
* Extraction: retrieves exact text or equations
* Computation: not performed in this sprint

If information is not written in the document, the system refuses to answer.

---

## What the App Does

### 1. Claim Verification (Strict)

* Verifies whether a claim is explicitly supported by the uploaded PDF
* Returns YES or NO
* Provides exact PDF page citations
* Returns “Not available in the document” if evidence is missing
* Never guesses or hallucinates

---

### 2. Retrieval-Augmented Generation (RAG)

* PDFs are chunked and embedded
* FAISS vector store is used for similarity search
* Top-K relevant chunks are retrieved
* The LLM answers strictly from retrieved context only

---

### 3. Tool Usage (Sprint 2 Compliant)

The system uses **LangChain StructuredTools** for core operations.

Tools implemented:

* retrieve_top_k
  Retrieves top-K relevant document chunks from the vector store

* embed_texts
  Generates embeddings for document indexing

* load_index_and_metadata
  Loads and inspects the vector index

Tools are:

* Deterministic
* Explicit
* Non-autonomous (no agents)

---

### 4. Equation Extraction (Text-Based PDFs Only)

When a verified claim is equation-related:

* Equations are extracted directly from the PDF text layer
* Supported formats:

  * LaTeX
  * ASCII
  * JSON structure
* Each equation includes page number and evidence text

Scanned or image-only PDFs are not supported in this sprint.

---

## Application Flow

1. Upload academic PDF(s)
2. Ask a question or claim
3. Tool retrieves relevant document chunks
4. LLM answers only using retrieved evidence
5. Citations and evidence are displayed
6. Equation extraction is triggered when applicable

---

## What This App Does NOT Do

* No OCR
* No image-based PDF processing
* No autonomous agents
* No symbolic or numeric computation
* No external knowledge usage

---

## Technology Stack

* Python
* Streamlit
* LangChain
* OpenAI API
* FAISS
* PDF text parsing

---

## Project Status

* RAG pipeline: Implemented
* Tool-based retrieval: Implemented
* Equation extraction (text-based): Implemented
* UI: Functional
* Agent-based autonomy: Intentionally excluded (Sprint 3)

---

## Rationale

The project prioritizes:

* Academic correctness
* Deterministic behavior
* Zero hallucination tolerance

If something is not explicitly written in the document, it is treated as non-existent.

---

## End of README
