"""Format-agnostic ingestion.

Turns a raw source document — plain text (our test-data stand-in for
already-extracted OCR text) or a PDF — into either plain text for the regex
extractor, or, for a ZUGFeRD/Factur-X e-invoice, the structured XML embedded
in the PDF/A-3 itself. Everything past this module deals in text or XML, never
file formats.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pdfplumber
from pypdf import PdfReader

# ZUGFeRD/Factur-X hybrid invoices embed their machine-readable data as a PDF
# attachment under one of these conventional names.
ZUGFERD_ATTACHMENT_NAMES = {"factur-x.xml", "zugferd-invoice.xml", "xrechnung.xml"}


@dataclass
class LoadedDoc:
    doc_id: str
    source_format: str  # "text" | "zugferd_xml"
    text: str | None = None
    xml: bytes | None = None


def load(path: Path) -> LoadedDoc:
    doc_id = path.stem
    suffix = path.suffix.lower()

    if suffix == ".txt":
        return LoadedDoc(doc_id, "text", text=path.read_text(encoding="utf-8"))

    if suffix == ".pdf":
        xml = _extract_zugferd_xml(path)
        if xml is not None:
            return LoadedDoc(doc_id, "zugferd_xml", xml=xml)
        return LoadedDoc(doc_id, "text", text=_extract_pdf_text(path))

    raise ValueError(f"Unsupported source format: {suffix} ({path})")


def _extract_zugferd_xml(path: Path) -> bytes | None:
    reader = PdfReader(str(path))
    for name, attachment in reader.attachments.items():
        if name.lower() in ZUGFERD_ATTACHMENT_NAMES:
            return attachment[0] if isinstance(attachment, list) else attachment
    return None


def _extract_pdf_text(path: Path) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)
