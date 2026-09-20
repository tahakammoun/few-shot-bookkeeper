"""Few-shot drafting.

Shows the model client_b's and client_c's (raw docs -> output report) pairs as
worked examples, then asks it to draft a new client's report in the same
pattern — but with a placeholder token standing in for every monetary amount
and date, never a digit the model computed or copied itself. The exact
placeholder tokens come from this project's own deterministic extract/
aggregate pipeline (src/placeholders.py), not invented by the model. The two
worked examples deliberately differ in VAT treatment (client_b: registered,
client_c: Kleinunternehmer/§19 UStG) so the model has to infer which pattern
fits the new client from their own documents, not default to either example.
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors

from src.aggregate import aggregate
from src.extract import extract
from src.loader import load
from src.placeholders import placeholder_values

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data" / "clients"
CATEGORIES_PATH = Path(__file__).parent.parent / "data" / "categories.md"
MODEL = "gemini-3.8-flash"
WORKED_EXAMPLE_CLIENTS = ("client_b", "client_c")


def _read_raw_docs(client_id: str) -> str:
    docs_dir = DATA_DIR / client_id / "raw_docs"
    parts = [
        f"--- {path.name} ---\n{path.read_text(encoding='utf-8')}"
        for path in sorted(docs_dir.glob("*.txt"))
    ]
    return "\n\n".join(parts)


def _read_expected_output(client_id: str) -> str:
    return (DATA_DIR / client_id / "expected_output" / "report.html").read_text(encoding="utf-8")


def build_prompt(client_id: str) -> tuple[str, list[str]]:
    docs_dir = DATA_DIR / client_id / "raw_docs"
    records = [extract(load(p)) for p in sorted(docs_dir.glob("*.txt"))]
    summary = aggregate(records)
    placeholders = sorted(placeholder_values(records, summary))

    examples = "".join(
        f"\n\n=== WORKED EXAMPLE: {example_id} — raw source documents ===\n"
        f"{_read_raw_docs(example_id)}\n\n"
        f"=== WORKED EXAMPLE: {example_id} — correct final report (HTML) ===\n"
        f"{_read_expected_output(example_id)}"
        for example_id in WORKED_EXAMPLE_CLIENTS
    )

    placeholder_list = "\n".join(f"- {{{{{name}}}}}" for name in placeholders)

    return (
        f"""You are drafting an annual Einnahmenüberschussrechnung (EÜR) report as a
single self-contained HTML document, in German, for a freelance/small-business client
in Germany.

Fixed category vocabulary (do not invent categories outside this list):
{CATEGORIES_PATH.read_text(encoding="utf-8")}

You are shown two worked examples below: each is a client's raw source documents,
followed by the correct final report we hand-verified for that client. Study their
structure, section order, table shapes, CSS styling, and tone. Notice they are NOT
identical: client_b is VAT-registered (Netto/USt/Brutto columns, a numeric
USt-Zahllast), while client_c is a Kleinunternehmer under §19 UStG (no VAT column,
"USt-Zahllast: entfällt"). Decide which pattern applies to the new client below based
on what their own documents show — do not default to either example.
{examples}

=== NEW CLIENT: {client_id} — raw source documents ===
{_read_raw_docs(client_id)}

=== YOUR TASK ===
Produce a single self-contained HTML document (inline <style>, matching the visual
language of the worked examples) for {client_id}, following the same section pattern:
Betriebseinnahmen, Betriebsausgaben nach Kategorie, a chart image
(<img src="chart_expenses.png">), Ergebnis, and a short narrative paragraph.

CRITICAL RULE — placeholders, not digits:
Every monetary amount and every date MUST be one of the EXACT placeholder tokens
listed below, written as {{{{token.name}}}} (e.g. {{{{income.total.net}}}}). Do not
compute, round, sum, or type any digit yourself for these values — not even to restate
a total. Do not invent new placeholder names and do not omit any listed one that the
report structure needs. Vendor names, invoice numbers, and category names may be
written directly since they are not computed figures.

Required placeholder tokens (use exactly these, nothing else):
{placeholder_list}

Output ONLY the HTML document, no explanation, no markdown code fences.
""",
        placeholders,
    )


MAX_ATTEMPTS = 5


def _generate_with_retry(client: genai.Client, prompt: str):
    for attempt in range(MAX_ATTEMPTS):
        try:
            return client.models.generate_content(model=MODEL, contents=prompt)
        except errors.ServerError:
            if attempt == MAX_ATTEMPTS - 1:
                raise
            time.sleep(2**attempt)  # 1s, 2s, 4s, 8s — Gemini overload is usually transient


def draft(client_id: str, out_path: Path) -> str:
    prompt, _ = build_prompt(client_id)

    client = genai.Client()
    response = _generate_with_retry(client, prompt)
    html = response.text.strip()
    html = re.sub(r"^```(?:html)?\n|\n```$", "", html)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return html


if __name__ == "__main__":
    client_id = sys.argv[1] if len(sys.argv) > 1 else "client_a"
    out_path = Path(__file__).parent.parent / "outputs" / f"{client_id}_draft.html"
    draft(client_id, out_path)
    print(f"Wrote {out_path}")
