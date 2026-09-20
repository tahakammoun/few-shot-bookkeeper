import pytest

from src.extract import Record
from src.review_app import OUTPUTS_DIR, _category_row, _overrides_from_form, app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_category_row_flags_needs_review():
    record = Record(
        doc_id="unknown_01",
        party="Wunderlich Gartenbau GmbH",
        date="12.03.2026",
        direction="expense",
        category="sonstiges",
        net=180.0,
        vat_rate=19.0,
        vat=34.2,
        gross=214.2,
        needs_review=True,
    )
    row_html = _category_row(record)
    assert "needs review" in row_html
    assert 'value="sonstiges" selected' in row_html


def test_category_row_no_flag_for_matched_category():
    record = Record(
        doc_id="office_01",
        party="Büro GmbH",
        date="01.01.2026",
        direction="expense",
        category="office_supplies",
        net=100.0,
        vat_rate=19.0,
        vat=19.0,
        gross=119.0,
        needs_review=False,
    )
    row_html = _category_row(record)
    assert "needs review" not in row_html


def test_overrides_from_form_extracts_category_fields():
    form = {"category__doc1": "travel", "reviewer_name": "Alex", "category__doc2": "software"}
    assert _overrides_from_form(form) == {"doc1": "travel", "doc2": "software"}


def test_review_form_lists_client_a_records(client):
    resp = client.get("/review/client_a")
    assert resp.status_code == 200
    assert b"jan_income_01" in resp.data


def test_full_review_flow_produces_an_approved_pdf(client):
    resp = client.post("/review/client_a/preview", data={"reviewer_name": "Alex Reviewer"})
    assert resp.status_code == 200
    assert b"Checker: all figures verified" in resp.data

    resp = client.post("/review/client_a/approve", data={"reviewer_name": "Alex Reviewer"})
    assert resp.status_code == 200
    assert b"Approved" in resp.data

    out_pdf = OUTPUTS_DIR / "client_a_report.pdf"
    assert out_pdf.exists()
    assert out_pdf.read_bytes()[:5] == b"%PDF-"

    approval = (OUTPUTS_DIR / "client_a_approval.txt").read_text(encoding="utf-8")
    assert "Alex Reviewer" in approval


def test_approve_without_name_is_rejected(client):
    resp = client.post("/review/client_a/approve", data={"reviewer_name": ""})
    assert resp.status_code == 400
