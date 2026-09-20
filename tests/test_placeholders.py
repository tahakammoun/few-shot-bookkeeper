from pathlib import Path

from src.aggregate import aggregate
from src.extract import extract
from src.loader import load
from src.placeholders import placeholder_values

CLIENT_A_DOCS = Path(__file__).parent.parent / "data" / "clients" / "client_a" / "raw_docs"


def _values():
    records = [extract(load(p)) for p in sorted(CLIENT_A_DOCS.glob("*"))]
    summary = aggregate(records)
    return placeholder_values(records, summary)


def test_income_placeholders_match_answer_key():
    values = _values()
    assert values["income.jan_income_01.net"] == "3.000,00"
    assert values["income.jan_income_01.date"] == "15.01.2026"
    assert values["income.total.net"] == "6.500,00"
    assert values["income.total.vat"] == "1.235,00"


def test_expense_category_placeholders_match_answer_key():
    values = _values()
    assert values["expenses.office_supplies.net"] == "450,00"
    assert values["expenses.office_supplies.vat"] == "85,50"
    assert values["expenses.travel.net"] == "350,00"
    assert values["expenses.total.net"] == "2.400,00"


def test_summary_placeholders_match_answer_key():
    values = _values()
    assert values["summary.net_result"] == "4.100,00"
    assert values["summary.ust_zahllast"] == "1.059,00"


def test_largest_expense_category_is_derived_not_guessed():
    values = _values()
    # consulting_external (1000.00 net) is the single biggest category for client_a
    assert values["expenses.largest_category.name"] == "consulting_external"


def test_no_placeholder_value_is_missing_or_empty_for_a_number():
    values = _values()
    for key, value in values.items():
        if key.endswith(".net") or key.endswith(".vat") or key.endswith(".gross"):
            assert value != ""
