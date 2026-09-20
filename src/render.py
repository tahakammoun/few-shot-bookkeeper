"""Renders a self-contained HTML+CSS report (see data/clients/*/expected_output/)
to PDF. Charts are already embedded as <img> in the HTML by the time this runs —
this step is pure HTML-to-PDF, nothing else.
"""

from __future__ import annotations

from pathlib import Path

from weasyprint import HTML


def render_pdf(html_path: Path, out_path: Path) -> None:
    HTML(str(html_path)).write_pdf(str(out_path))
