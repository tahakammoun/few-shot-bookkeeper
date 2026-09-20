import pypdf
import pytest

from src.loader import load


def test_txt_loads_as_plain_text(tmp_path):
    p = tmp_path / "doc.txt"
    p.write_text("Nettobetrag: 100,00 EUR", encoding="utf-8")

    doc = load(p)

    assert doc.source_format == "text"
    assert doc.text == "Nettobetrag: 100,00 EUR"


def test_zugferd_pdf_is_detected_via_embedded_xml(tmp_path):
    xml_bytes = b"<invoice>fixture</invoice>"
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_attachment("factur-x.xml", xml_bytes)
    pdf_path = tmp_path / "invoice.pdf"
    with pdf_path.open("wb") as f:
        writer.write(f)

    doc = load(pdf_path)

    assert doc.source_format == "zugferd_xml"
    assert doc.xml == xml_bytes


def test_unsupported_format_raises(tmp_path):
    p = tmp_path / "doc.docx"
    p.write_text("irrelevant", encoding="utf-8")

    with pytest.raises(ValueError):
        load(p)
