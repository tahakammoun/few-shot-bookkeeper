from pathlib import Path

from src.extract import extract
from src.loader import LoadedDoc

FIXTURE = Path(__file__).parent / "fixtures" / "zugferd_software_invoice.xml"


def test_zugferd_invoice_extracts_structured_fields():
    doc = LoadedDoc(doc_id="zugferd_software_invoice", source_format="zugferd_xml", xml=FIXTURE.read_bytes())

    record = extract(doc)

    assert record.party == "CloudSuite Software Solutions"
    assert record.direction == "expense"
    assert record.category == "software"
    assert record.net == 200.0
    assert record.vat == 38.0
    assert record.gross == 238.0
    assert record.vat_rate == 19.0
