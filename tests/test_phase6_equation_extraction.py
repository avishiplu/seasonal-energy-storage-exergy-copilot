from src.retrieval.equation_extract import extract_equation_lines

def test_extract_equation_lines_basic():
    text = "Some text\nEx = Q*(1 - T0/Tb)\nMore text"
    eqs = extract_equation_lines(text)
    assert any("Ex" in e and "=" in e for e in eqs)

