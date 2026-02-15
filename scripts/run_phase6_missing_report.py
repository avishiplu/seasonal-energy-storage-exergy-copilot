from __future__ import annotations

from src.retrieval.sprint2_retriever_adapter import Sprint2RetrieverAdapter
from src.retrieval.equation_extract import retrieve_equations

def main():
    retriever = Sprint2RetrieverAdapter()

    query = "Carnot factor exergy of heat equation 1 - T0/T"
    eqs = retrieve_equations(retriever=retriever, query=query, k=8)

    print(f"Found {len(eqs)} equation candidates\n")
    for i, e in enumerate(eqs[:20], start=1):
        print(f"[{i}] {e.pdf_name} p.{e.page}")
        print(f"    {e.equation_text}")
        print(f"    ctx: {e.context_snippet}\n")

if __name__ == "__main__":
    main()
