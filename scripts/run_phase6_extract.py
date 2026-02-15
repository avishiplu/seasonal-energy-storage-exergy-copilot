from src.retrieval.sprint2_retriever_adapter import Sprint2RetrieverAdapter
from src.retrieval.equation_extract import retrieve_equations
from src.rag.retriever import retrieve_top_k


def is_good_candidate(s: str) -> bool:
    s_low = s.lower()
    if "temperature is" in s_low:
        return False
    if "fig." in s_low or "figure" in s_low:
        return False
    return any(tok in s for tok in ["=", "EX", "Ex", "T0", "ln", "COP", "eta", "Q", "m"])


def main():
    retriever = Sprint2RetrieverAdapter()
    query = "exergy balance equation"
    k = 8

    # --- RAW preview ---
    rows = retrieve_top_k(query=query, k=3)
    print(f"RAW chunks: {len(rows)}\n")
    for i, r in enumerate(rows, 1):
        print(f"[RAW {i}] {r.get('source_file')} p.{r.get('page')}")
        print((r.get("text") or "")[:300].replace("\n", " "))
        print()

    # --- equation extraction ---
    eqs = retrieve_equations(retriever=retriever, query=query, k=k)

    # --- quick filter (NOW eqs exists) ---
    eqs = [e for e in eqs if is_good_candidate(e.equation_text)]

    print(f"\nFound {len(eqs)} equation candidates (after quick filter)\n")
    for i, e in enumerate(eqs[:10], start=1):
        print(f"[{i}] {e.pdf_name} p.{e.page}")
        print(f"    {e.equation_text}")
        print(f"    ctx: {e.context_snippet}\n")


if __name__ == "__main__":
    main()
