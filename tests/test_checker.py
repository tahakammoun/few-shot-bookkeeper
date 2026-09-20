import shutil
from pathlib import Path

from src.aggregate import aggregate
from src.checker import check
from src.extract import extract
from src.inject import inject
from src.loader import load
from src.placeholders import placeholder_values

FIXTURE_DRAFT = Path(__file__).parent / "fixtures" / "client_a_draft_placeholder_only.html"
DATA_DIR = Path(__file__).parent.parent / "data" / "clients"


def _client_a_values():
    docs_dir = DATA_DIR / "client_a" / "raw_docs"
    records = [extract(load(p)) for p in sorted(docs_dir.glob("*.txt"))]
    return placeholder_values(records, aggregate(records))


def test_check_passes_on_a_correctly_injected_report():
    draft = FIXTURE_DRAFT.read_text(encoding="utf-8")
    final_html = inject(draft, _client_a_values())

    result = check(final_html, "client_a", DATA_DIR)

    assert result.ok
    assert result.missing_values == []
    assert result.leftover_placeholders == []


def test_check_catches_an_unsubstituted_placeholder():
    # Simulates injection missing a spot: only one token got replaced.
    draft = FIXTURE_DRAFT.read_text(encoding="utf-8")
    values = _client_a_values()
    final_html = draft.replace(
        "{{income.jan_income_01.date}}", values["income.jan_income_01.date"]
    )  # every other {{token}} deliberately left un-substituted

    result = check(final_html, "client_a", DATA_DIR)

    assert not result.ok
    assert result.leftover_placeholders  # still full of {{...}} tokens


def test_check_catches_a_source_document_that_changed_after_the_draft_was_made(tmp_path):
    # The original Session-4 requirement: deliberately break something in a
    # raw invoice and confirm the checker actually catches it.
    tampered_clients_dir = tmp_path / "clients"
    shutil.copytree(DATA_DIR / "client_a", tampered_clients_dir / "client_a")

    invoice = tampered_clients_dir / "client_a" / "raw_docs" / "jan_income_01.txt"
    original_text = invoice.read_text(encoding="utf-8")
    tampered_text = original_text.replace("Nettobetrag: 3000,00 EUR", "Nettobetrag: 3500,00 EUR")
    assert tampered_text != original_text  # sanity: the replace actually matched
    invoice.write_text(tampered_text, encoding="utf-8")

    # final_html was produced BEFORE the tampering, from the true original numbers.
    draft = FIXTURE_DRAFT.read_text(encoding="utf-8")
    final_html = inject(draft, _client_a_values())

    result = check(final_html, "client_a", tampered_clients_dir)

    assert not result.ok
    assert any("income.jan_income_01.net" in m for m in result.missing_values)
    assert any("income.total.net" in m for m in result.missing_values)
