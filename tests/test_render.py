from pathlib import Path

from src.render import render_pdf

REPORT = Path(__file__).parent.parent / "data" / "clients" / "client_b" / "expected_output" / "report.html"


def test_render_pdf_produces_a_valid_pdf(tmp_path):
    out = tmp_path / "report.pdf"

    render_pdf(REPORT, out)

    assert out.exists()
    assert out.read_bytes()[:5] == b"%PDF-"
