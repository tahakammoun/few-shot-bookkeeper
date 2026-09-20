"""CLI entry point: python run.py <client_id> prints the client's EÜR summary."""

from __future__ import annotations

import sys
from pathlib import Path

from src.aggregate import aggregate
from src.extract import extract
from src.loader import load

DATA_DIR = Path(__file__).parent / "data" / "clients"


def run(client_id: str) -> None:
    raw_docs_dir = DATA_DIR / client_id / "raw_docs"
    records = [extract(load(path)) for path in sorted(raw_docs_dir.glob("*"))]
    summary = aggregate(records)

    print(f"Income net: {summary.income.net} VAT: {summary.income.vat}")
    print(f"Expenses net: {summary.expenses.net} VAT (Vorsteuer): {summary.expenses.vat}")
    print(f"Net result: {summary.net_result}")
    print(f"USt-Zahllast: {summary.ust_zahllast}")

    print("\nExpenses by category:")
    for category, totals in sorted(summary.expenses_by_category.items()):
        print(f"  {category}: net {totals.net} vat {totals.vat} gross {totals.gross}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python run.py <client_id>")
    run(sys.argv[1])
