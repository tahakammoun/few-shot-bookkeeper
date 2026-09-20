from src.extract import extract
from src.loader import LoadedDoc

UNRECOGNIZED_VENDOR_INVOICE = """Wunderlich Gartenbau GmbH
Rechnung Nr. 2026-9981
Datum: 12.03.2026

Bepflanzung Bueroeingang

Nettobetrag: 180,00 EUR
USt (19%): 34,20 EUR
Rechnungsbetrag: 214,20 EUR
"""


def test_unrecognized_vendor_falls_back_to_sonstiges_and_is_flagged():
    doc = LoadedDoc(doc_id="unknown_vendor", source_format="text", text=UNRECOGNIZED_VENDOR_INVOICE)

    record = extract(doc)  # must not raise

    assert record.category == "sonstiges"
    assert record.needs_review is True
    assert record.net == 180.0  # extraction itself still succeeds — only categorization is uncertain


def test_recognized_vendor_is_not_flagged():
    doc = LoadedDoc(
        doc_id="known_vendor",
        source_format="text",
        text="BÜROBEDARF SCHMIDT GmbH\nNettobetrag: 100,00 EUR\nUSt (19%): 19,00 EUR\n",
    )

    record = extract(doc)

    assert record.category == "office_supplies"
    assert record.needs_review is False
