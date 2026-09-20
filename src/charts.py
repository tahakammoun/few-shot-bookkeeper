"""Chart rendering for the client-readable section of the output PDF.

Kept deliberately separate from the Finanzamt-style tables (see templates/) —
charts are for the human-readable summary only, never a source of truth for a
number that also appears in the tables.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

CATEGORY_COLORS = {
    "office_supplies": "#4C72B0",
    "travel": "#55A868",
    "software": "#C44E52",
    "catering": "#8172B2",
    "consulting_external": "#CCB974",
}


def expenses_by_category_chart(totals: dict[str, float], out_path: Path) -> None:
    categories = sorted(totals)
    values = [totals[c] for c in categories]
    colors = [CATEGORY_COLORS.get(c, "#777777") for c in categories]

    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.bar(categories, values, color=colors)
    ax.set_ylabel("EUR (netto)")
    ax.set_title("Betriebsausgaben nach Kategorie")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
