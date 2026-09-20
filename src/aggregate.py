"""Sums extracted records into the EÜR totals: income/expenses by category,
net result (Überschuss), and USt-Zahllast (VAT payable = income VAT − Vorsteuer).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from src.extract import Record


@dataclass
class Totals:
    net: float
    vat: float

    @property
    def gross(self) -> float:
        return round(self.net + self.vat, 2)


@dataclass
class EuerSummary:
    income: Totals
    income_by_category: dict[str, Totals]
    expenses: Totals
    expenses_by_category: dict[str, Totals]

    @property
    def net_result(self) -> float:
        return round(self.income.net - self.expenses.net, 2)

    @property
    def ust_zahllast(self) -> float:
        return round(self.income.vat - self.expenses.vat, 2)


def aggregate(records: list[Record]) -> EuerSummary:
    income_by_category: dict[str, Totals] = defaultdict(lambda: Totals(0.0, 0.0))
    expenses_by_category: dict[str, Totals] = defaultdict(lambda: Totals(0.0, 0.0))

    for record in records:
        bucket = income_by_category if record.direction == "income" else expenses_by_category
        current = bucket[record.category]
        bucket[record.category] = Totals(
            round(current.net + record.net, 2),
            round(current.vat + record.vat, 2),
        )

    return EuerSummary(
        income=_sum_totals(income_by_category.values()),
        income_by_category=dict(income_by_category),
        expenses=_sum_totals(expenses_by_category.values()),
        expenses_by_category=dict(expenses_by_category),
    )


def _sum_totals(totals) -> Totals:
    totals = list(totals)
    return Totals(
        round(sum(t.net for t in totals), 2),
        round(sum(t.vat for t in totals), 2),
    )
