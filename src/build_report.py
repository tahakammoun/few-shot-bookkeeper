"""Final assembly: draft HTML (from src.draft, or a stand-in) -> inject real
numbers -> check independently -> render to PDF. Refuses to render if the
checker finds anything wrong — nothing reaches outputs/ unverified.

prepare_report() does everything except the render, so the review UI can show
a human the checked HTML before committing to a PDF, and can pass corrected
categories in without re-running extraction from scratch.
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

from src.aggregate import EuerSummary, aggregate
from src.charts import expenses_by_category_chart
from src.checker import CheckResult, check
from src.extract import Record, extract
from src.inject import inject
from src.loader import load
from src.placeholders import placeholder_values
from src.render import render_pdf

DATA_DIR = Path(__file__).parent.parent / "data" / "clients"


class CheckFailedError(Exception):
    """Raised when the checker finds a mismatch — the report is not rendered."""


def load_records(client_id: str, category_overrides: dict[str, str] | None = None) -> list[Record]:
    docs_dir = DATA_DIR / client_id / "raw_docs"
    records = [extract(load(p)) for p in sorted(docs_dir.glob("*.txt"))]
    if category_overrides:
        records = [
            dataclasses.replace(r, category=category_overrides[r.doc_id], needs_review=False)
            if r.doc_id in category_overrides
            else r
            for r in records
        ]
    return records


def prepare_report(
    client_id: str,
    draft_html_path: Path,
    category_overrides: dict[str, str] | None = None,
) -> tuple[str, list[Record], EuerSummary, CheckResult]:
    records = load_records(client_id, category_overrides)
    summary = aggregate(records)
    values = placeholder_values(records, summary)

    draft_html = draft_html_path.read_text(encoding="utf-8")
    final_html = inject(draft_html, values)

    result = check(final_html, client_id, DATA_DIR)
    return final_html, records, summary, result


def build_report(client_id: str, draft_html_path: Path, out_pdf_path: Path) -> Path:
    final_html, _records, summary, result = prepare_report(client_id, draft_html_path)
    if not result.ok:
        raise CheckFailedError(
            f"missing_values={result.missing_values} "
            f"leftover_placeholders={result.leftover_placeholders}"
        )
    render_report(final_html, summary, out_pdf_path)
    return out_pdf_path


def render_report(final_html: str, summary: EuerSummary, out_pdf_path: Path) -> None:
    out_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    html_path = out_pdf_path.with_suffix(".html")
    html_path.write_text(final_html, encoding="utf-8")

    # The chart lives next to the HTML: render_pdf resolves <img src="chart_expenses.png">
    # relative to the HTML file's own location.
    chart_path = html_path.parent / "chart_expenses.png"
    expenses_by_category_chart({cat: t.net for cat, t in summary.expenses_by_category.items()}, chart_path)

    render_pdf(html_path, out_pdf_path)


if __name__ == "__main__":
    client_id = sys.argv[1] if len(sys.argv) > 1 else "client_a"
    outputs_dir = Path(__file__).parent.parent / "outputs"
    draft_path = Path(sys.argv[2]) if len(sys.argv) > 2 else outputs_dir / f"{client_id}_draft.html"
    out_pdf = outputs_dir / f"{client_id}_report.pdf"

    path = build_report(client_id, draft_path, out_pdf)
    print(f"Wrote {path}")
