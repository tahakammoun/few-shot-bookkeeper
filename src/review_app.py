"""The human checkpoint: nothing reaches a client without a named reviewer
seeing the draft and approving it. Shows the checked report (numbers,
narrative, chart), lets a reviewer correct any record the extractor couldn't
confidently categorize (needs_review=True — see extract.py's "sonstiges"
fallback), and only renders the final PDF once a name is typed in.

Flow: GET /review/<client_id> (correct categories) -> POST .../preview
(shows the checked report) -> POST .../approve (renders PDF, records who
approved it and when).
"""

from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, abort, redirect, render_template_string, request, send_from_directory, url_for

from src.build_report import DATA_DIR, load_records, prepare_report, render_report

OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"
FIXTURE_DRAFT = Path(__file__).parent.parent / "tests" / "fixtures" / "client_a_draft_placeholder_only.html"

# Must stay in sync with data/categories.md's EXPENSES list.
EXPENSE_CATEGORIES = ["office_supplies", "travel", "software", "catering", "consulting_external", "sonstiges"]

app = Flask(__name__)

PAGE_SHELL = """
<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{{ title }}</title>
<style>
  :root { --ink:#1f2937; --muted:#6b7280; --accent:#1e3a5f; --line:#d1d5db; --bg:#f4f6f9;
          --flag-bg:#fbf1de; --flag-border:#b8720f; --good:#257a52; --bad:#a23b3b; }
  body { font-family:"Helvetica Neue",Arial,sans-serif; color:var(--ink); background:var(--bg);
         margin:0; padding:32px 24px 64px; }
  main { max-width:760px; margin:0 auto; background:#fff; border:1px solid var(--line);
         border-radius:10px; padding:28px 32px; }
  h1 { font-size:21px; color:var(--accent); margin:0 0 6px; }
  h2 { font-size:15px; color:var(--accent); margin:28px 0 10px; border-bottom:1px solid var(--line); padding-bottom:6px; }
  p.lede { color:var(--muted); font-size:13.5px; margin:0 0 20px; }
  table { width:100%; border-collapse:collapse; font-size:13.5px; }
  th, td { text-align:left; padding:8px 6px; border-bottom:1px solid var(--line); vertical-align:middle; }
  tr.flagged { background:var(--flag-bg); }
  .flag-badge { display:inline-block; font-size:10.5px; font-weight:600; color:var(--flag-border);
                border:1px solid var(--flag-border); border-radius:4px; padding:1px 6px; margin-left:6px; }
  select, input[type=text] { font:inherit; padding:6px 8px; border:1px solid var(--line); border-radius:6px; }
  label { font-size:13px; color:var(--muted); display:block; margin:16px 0 6px; }
  button { font:inherit; font-weight:600; background:var(--accent); color:#fff; border:none;
           border-radius:6px; padding:10px 18px; cursor:pointer; margin-top:20px; }
  button.secondary { background:#fff; color:var(--accent); border:1px solid var(--accent); }
  .status { padding:10px 14px; border-radius:6px; font-size:13.5px; margin:14px 0; }
  .status.ok { background:#e8f5ee; color:var(--good); }
  .status.fail { background:#fbeaea; color:var(--bad); }
  iframe { width:100%; height:520px; border:1px solid var(--line); border-radius:8px; margin-top:12px; }
  code { background:#eef1f6; padding:1px 5px; border-radius:4px; font-size:12.5px; }
  .clients a { display:inline-block; margin-right:12px; }
</style></head><body><main>{{ body|safe }}</main></body></html>
"""


def render_page(title: str, body: str) -> str:
    return render_template_string(PAGE_SHELL, title=title, body=body)


def _draft_path_for(client_id: str) -> Path:
    real_draft = OUTPUTS_DIR / f"{client_id}_draft.html"
    if real_draft.exists():
        return real_draft
    if client_id == "client_a":
        return FIXTURE_DRAFT  # stand-in until the live drafter succeeds — see README
    abort(404, f"No draft found for {client_id} (expected {real_draft})")


@app.route("/")
def index():
    clients = sorted(p.name for p in DATA_DIR.iterdir() if p.is_dir())
    links = "".join(f'<a href="{url_for("review_form", client_id=c)}">{c}</a>' for c in clients)
    return render_page("Review", f"<h1>Reports awaiting review</h1><p class='lede'>Pick a client.</p><div class='clients'>{links}</div>")


@app.route("/review/<client_id>")
def review_form(client_id: str):
    records = load_records(client_id)
    rows = "".join(_category_row(r) for r in records)
    flagged_count = sum(1 for r in records if r.needs_review)
    notice = f"<p class='lede'>{flagged_count} record(s) need a category picked by hand.</p>" if flagged_count else "<p class='lede'>Nothing flagged — all categories matched automatically.</p>"

    body = f"""
      <h1>Review: {html.escape(client_id)}</h1>
      {notice}
      <form method="post" action="{url_for('preview', client_id=client_id)}">
        <h2>Extracted records</h2>
        <table>
          <tr><th>Doc</th><th>Party</th><th>Amount (net)</th><th>Category</th></tr>
          {rows}
        </table>
        <label for="reviewer_name">Your name</label>
        <input type="text" id="reviewer_name" name="reviewer_name" placeholder="required before approval" required>
        <button type="submit">Generate preview</button>
      </form>
    """
    return render_page(f"Review {client_id}", body)


def _category_row(record) -> str:
    row_class = "flagged" if record.needs_review else ""
    badge = '<span class="flag-badge">needs review</span>' if record.needs_review else ""
    options = "".join(
        f'<option value="{c}" {"selected" if c == record.category else ""}>{c}</option>' for c in EXPENSE_CATEGORIES
    )
    if record.direction == "income":
        category_cell = "beratung (income)"
    else:
        category_cell = f'<select name="category__{html.escape(record.doc_id)}">{options}</select>{badge}'
    return (
        f"<tr class='{row_class}'><td><code>{html.escape(record.doc_id)}</code></td>"
        f"<td>{html.escape(record.party)}</td><td>{record.net:.2f}</td><td>{category_cell}</td></tr>"
    )


def _overrides_from_form(form) -> dict[str, str]:
    prefix = "category__"
    return {k[len(prefix):]: v for k, v in form.items() if k.startswith(prefix)}


@app.route("/review/<client_id>/preview", methods=["POST"])
def preview(client_id: str):
    overrides = _overrides_from_form(request.form)
    reviewer_name = request.form.get("reviewer_name", "").strip()

    final_html, _records, summary, result = prepare_report(client_id, _draft_path_for(client_id), overrides)
    render_report(final_html, summary, OUTPUTS_DIR / f"{client_id}_preview.pdf")  # writes preview .html + chart too

    status_html = (
        "<div class='status ok'>Checker: all figures verified against the raw documents.</div>"
        if result.ok
        else f"<div class='status fail'>Checker found problems: {html.escape(str(result.missing_values + result.leftover_placeholders))}</div>"
    )

    hidden_overrides = "".join(
        f'<input type="hidden" name="category__{html.escape(k)}" value="{html.escape(v)}">' for k, v in overrides.items()
    )
    approve_disabled = "" if result.ok else "disabled"

    body = f"""
      <h1>Preview: {html.escape(client_id)}</h1>
      {status_html}
      <iframe src="{url_for('serve_output', filename=f'{client_id}_preview.html')}"></iframe>
      <form method="post" action="{url_for('approve', client_id=client_id)}">
        {hidden_overrides}
        <input type="hidden" name="reviewer_name" value="{html.escape(reviewer_name)}">
        <p class='lede' style="margin-top:16px">Approving as <strong>{html.escape(reviewer_name) or '(no name entered)'}</strong></p>
        <button type="submit" {approve_disabled}>Approve &amp; generate PDF</button>
        <button type="button" class="secondary" onclick="history.back()">Back</button>
      </form>
    """
    return render_page(f"Preview {client_id}", body)


@app.route("/review/<client_id>/approve", methods=["POST"])
def approve(client_id: str):
    overrides = _overrides_from_form(request.form)
    reviewer_name = request.form.get("reviewer_name", "").strip()
    if not reviewer_name:
        abort(400, "A reviewer name is required before approval.")

    final_html, _records, summary, result = prepare_report(client_id, _draft_path_for(client_id), overrides)
    if not result.ok:
        abort(400, "Checker failed — cannot approve an unverified report.")

    approved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    signed_html = final_html.replace(
        "</footer>",
        f"<br>Geprüft und freigegeben von: {html.escape(reviewer_name)} am {approved_at}</footer>",
    )
    out_pdf = OUTPUTS_DIR / f"{client_id}_report.pdf"
    render_report(signed_html, summary, out_pdf)
    (OUTPUTS_DIR / f"{client_id}_approval.txt").write_text(
        f"Client: {client_id}\nApproved by: {reviewer_name}\nApproved at: {approved_at}\n", encoding="utf-8"
    )

    body = f"""
      <h1>Approved</h1>
      <div class="status ok">{html.escape(client_id)}'s report was approved by {html.escape(reviewer_name)} and rendered.</div>
      <p class='lede'><a href="{url_for('serve_output', filename=out_pdf.name)}">Download the PDF</a></p>
    """
    return render_page("Approved", body)


@app.route("/outputs/<path:filename>")
def serve_output(filename: str):
    return send_from_directory(OUTPUTS_DIR, filename)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
