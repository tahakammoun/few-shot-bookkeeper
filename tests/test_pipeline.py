"""Locks in the aggregation math: the text-based pipeline (loader -> extract ->
aggregate) run against client_a's raw docs must reproduce answer_key.md exactly.
"""

from pathlib import Path

from src.aggregate import aggregate
from src.extract import extract
from src.loader import load

CLIENT_A_DOCS = Path(__file__).parent.parent / "data" / "clients" / "client_a" / "raw_docs"


def _summary():
    records = [extract(load(p)) for p in sorted(CLIENT_A_DOCS.glob("*"))]
    return aggregate(records)


def test_income_totals_match_answer_key():
    summary = _summary()
    assert summary.income.net == 6500.0
    assert summary.income.vat == 1235.0


def test_expense_totals_match_answer_key():
    summary = _summary()
    assert summary.expenses.net == 2400.0
    assert summary.expenses.vat == 176.0


def test_expense_categories_match_answer_key():
    summary = _summary()
    expected = {
        "office_supplies": (450.0, 85.5),
        "travel": (350.0, 24.5),
        "software": (200.0, 38.0),
        "catering": (400.0, 28.0),
        "consulting_external": (1000.0, 0.0),
    }
    for category, (net, vat) in expected.items():
        totals = summary.expenses_by_category[category]
        assert totals.net == net
        assert totals.vat == vat


def test_net_result_and_ust_zahllast():
    summary = _summary()
    assert summary.net_result == 4100.0
    assert summary.ust_zahllast == 1059.0
