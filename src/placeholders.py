"""The placeholder schema shared between the few-shot drafter and the (future)
number-injection step: the exact set of {{ tokens }} the model is allowed to
use in place of a monetary amount or a date. Generated from the same
Records/EuerSummary the deterministic pipeline already computed — never
invented by the model, and never something it has to compute itself.

Vendor names, invoice/Beleg identifiers, and category names are deliberately
NOT placeholders: they're copied text, not arithmetic, so they're outside the
"never trust the model's digits" guarantee this schema exists to enforce.
"""

from __future__ import annotations

from src.aggregate import EuerSummary
from src.extract import Record


def placeholder_values(records: list[Record], summary: EuerSummary) -> dict[str, str]:
    values: dict[str, str] = {}

    income_records = sorted((r for r in records if r.direction == "income"), key=lambda r: r.doc_id)
    for r in income_records:
        values[f"income.{r.doc_id}.date"] = _fmt_date(r.date)
        values[f"income.{r.doc_id}.net"] = _fmt_amount(r.net)
        values[f"income.{r.doc_id}.vat"] = _fmt_amount(r.vat)
        values[f"income.{r.doc_id}.gross"] = _fmt_amount(r.gross)

    values["income.total.net"] = _fmt_amount(summary.income.net)
    values["income.total.vat"] = _fmt_amount(summary.income.vat)
    values["income.total.gross"] = _fmt_amount(summary.income.gross)

    for category, totals in sorted(summary.expenses_by_category.items()):
        values[f"expenses.{category}.net"] = _fmt_amount(totals.net)
        values[f"expenses.{category}.vat"] = _fmt_amount(totals.vat)
        values[f"expenses.{category}.gross"] = _fmt_amount(totals.gross)

    values["expenses.total.net"] = _fmt_amount(summary.expenses.net)
    values["expenses.total.vat"] = _fmt_amount(summary.expenses.vat)
    values["expenses.total.gross"] = _fmt_amount(summary.expenses.gross)

    values["summary.net_result"] = _fmt_amount(summary.net_result)
    values["summary.ust_zahllast"] = _fmt_amount(summary.ust_zahllast)

    if summary.expenses_by_category:
        largest = max(summary.expenses_by_category, key=lambda c: summary.expenses_by_category[c].net)
        values["expenses.largest_category.name"] = largest

    return values


def _fmt_amount(amount: float) -> str:
    # German number formatting to match the worked examples: "1.234,56"
    whole, _, cents = f"{amount:,.2f}".partition(".")
    whole = whole.replace(",", ".")
    return f"{whole},{cents}"


def _fmt_date(date: str | None) -> str:
    # extract.py's DATE_RE yields dd.mm.yyyy, dd/mm/yyyy, or yyyy-mm-dd as found
    # in the source doc; normalize all of them to dd.mm.yyyy for the report.
    if date is None:
        return ""
    if "-" in date:
        year, month, day = date.split("-")
        return f"{day}.{month}.{year}"
    return date.replace("/", ".")
