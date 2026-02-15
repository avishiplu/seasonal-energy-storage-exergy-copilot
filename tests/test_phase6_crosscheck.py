from src.retrieval.equation_codegen import EquationSpec, EquationStatus, cross_check_equations
from src.core.values import Citation

def test_crosscheck_marks_ambiguous_on_mismatch():
    c = Citation(pdf_name="x.pdf", page=1, chunk_id="c1")
    e1 = EquationSpec(name="A", raw="y = 2*n", variables=["y","n"], citation=c, status=EquationStatus.FOUND)
    e2 = EquationSpec(name="A", raw="y = 2/n", variables=["y","n"], citation=c, status=EquationStatus.FOUND)
    out = cross_check_equations([e1, e2])
    assert all(o.status == EquationStatus.AMBIGUOUS for o in out)
