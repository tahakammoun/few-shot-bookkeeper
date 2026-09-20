"""Deterministic field extraction.

Turns a LoadedDoc into a structured Record — vendor/party, date, direction,
category, net/VAT/gross — regardless of whether it came from free text (regex
over labeled amount lines) or a ZUGFeRD e-invoice (structured XML, read
directly off the standard CII fields, no guessing required).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from lxml import etree

from src.loader import LoadedDoc

CII_NS = {
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
}

# Keyword -> EÜR category, checked against the whole document (text case) or
# the seller name (ZUGFeRD case). Must stay in sync with data/categories.md.
CATEGORY_KEYWORDS = (
    ("office_supplies", ("büromaterial", "büro", "papier", "toner", "ordner", "aktenmappen", "drucker")),
    ("travel", ("fahrschein", "reise", "travel", "sparpreis", " ice", "bahn", "mobility")),
    ("software", ("software", "subscription", "cloud", "saas")),
    ("catering", ("catering", "verpflegung")),
    ("consulting_external", ("external code review", "consulting external", "reverse charge", "nordicdev")),
)

NET_LABELS = ("nettobetrag", "net amount", "netto", "subtotal", "zwischensumme", "preis (net")
VAT_LABELS = ("ust", "vat", "mwst", "umsatzsteuer")
GROSS_LABELS = ("rechnungsbetrag", "total", "gesamtbetrag", "gesamt")
INCOME_LABELS = ("an:", "bill to:")

AMOUNT_RE = re.compile(r"([\d][\d\s.,]*\d)\s*EUR")
VAT_RATE_RE = re.compile(r"\((\d+)\s*%\)")
DATE_RE = re.compile(r"(\d{2}[./]\d{2}[./]\d{4}|\d{4}-\d{2}-\d{2})")


@dataclass
class Record:
    doc_id: str
    party: str
    date: str | None
    direction: str  # "income" | "expense"
    category: str
    net: float
    vat_rate: float | None
    vat: float
    gross: float
    needs_review: bool = False


def extract(doc: LoadedDoc) -> Record:
    if doc.source_format == "zugferd_xml":
        return _extract_zugferd(doc)
    return _extract_text(doc)


def _normalize_amount(raw: str) -> float:
    # Collapses OCR-style stray spaces inside a number ("1 00,00" -> "100,00"),
    # then figures out which of , / . is the decimal separator.
    s = raw.replace(" ", "")
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    return float(s)


def _classify_category(text: str) -> tuple[str, bool]:
    """Returns (category, matched). matched=False means no keyword hit and the
    category fell back to the "sonstiges" catch-all — never trust that
    silently, it needs a human to actually look at the document."""
    lowered = text.lower()
    for category, keywords in CATEGORY_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return category, True
    return "sonstiges", False


def _extract_text(doc: LoadedDoc) -> Record:
    text = doc.text
    lines = text.splitlines()

    net = vat = gross = None
    vat_rate = None
    for line in lines:
        lowered = line.lower()
        match = AMOUNT_RE.search(line)
        if not match:
            continue
        amount = _normalize_amount(match.group(1))
        # NET before GROSS: "Subtotal" contains "total", so a looser gross
        # check first would misclassify it as the gross amount.
        if any(label in lowered for label in VAT_LABELS):
            vat = amount
            rate_match = VAT_RATE_RE.search(line)
            if rate_match:
                vat_rate = float(rate_match.group(1))
        elif any(label in lowered for label in NET_LABELS):
            net = amount
        elif any(label in lowered for label in GROSS_LABELS):
            gross = amount

    if net is None or vat is None:
        raise ValueError(f"Could not extract net/VAT from document {doc.doc_id}")
    if gross is None:
        gross = round(net + vat, 2)

    lowered_text = text.lower()
    needs_review = False
    if any(label in lowered_text for label in INCOME_LABELS):
        direction = "income"
        category = "beratung"
        party = _party_after_label(lines, INCOME_LABELS)
    else:
        direction = "expense"
        category, matched = _classify_category(text)
        needs_review = not matched
        party = next((line.strip() for line in lines if line.strip()), doc.doc_id)

    date_match = DATE_RE.search(text)
    date = date_match.group(1) if date_match else None

    return Record(doc.doc_id, party, date, direction, category, net, vat_rate, vat, gross, needs_review)


def _party_after_label(lines: list[str], labels: tuple[str, ...]) -> str:
    for line in lines:
        lowered = line.lower()
        for label in labels:
            if lowered.startswith(label):
                return line.split(":", 1)[1].strip()
    return "unknown"


def _cii_text(root, path: str) -> str | None:
    node = root.find(path, CII_NS)
    return node.text if node is not None else None


def _extract_zugferd(doc: LoadedDoc) -> Record:
    root = etree.fromstring(doc.xml)

    seller = _cii_text(
        root,
        "rsm:SupplyChainTradeTransaction/ram:ApplicableHeaderTradeAgreement"
        "/ram:SellerTradeParty/ram:Name",
    )
    summation_path = (
        "rsm:SupplyChainTradeTransaction/ram:ApplicableHeaderTradeSettlement"
        "/ram:SpecifiedTradeSettlementHeaderMonetarySummation"
    )
    net = float(_cii_text(root, f"{summation_path}/ram:TaxBasisTotalAmount"))
    vat = float(_cii_text(root, f"{summation_path}/ram:TaxTotalAmount"))
    gross = float(_cii_text(root, f"{summation_path}/ram:GrandTotalAmount"))

    rate_text = _cii_text(
        root,
        "rsm:SupplyChainTradeTransaction/ram:ApplicableHeaderTradeSettlement"
        "/ram:ApplicableTradeTax/ram:RateApplicablePercent",
    )
    vat_rate = float(rate_text) if rate_text else None

    date = _cii_text(root, "rsm:ExchangedDocument/ram:IssueDateTime/udt:DateTimeString")

    # ZUGFeRD e-invoices arrive from vendors we're paying, not ones we issue
    # ourselves — always the buyer side, so always an expense.
    category, matched = _classify_category(seller or "")

    return Record(
        doc_id=doc.doc_id,
        party=seller or "unknown",
        date=date,
        direction="expense",
        category=category,
        net=net,
        vat_rate=vat_rate,
        vat=vat,
        gross=gross,
        needs_review=not matched,
    )
