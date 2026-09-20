"""Independently re-verifies a final (post-injection) report against the raw
source documents — the last line of defense before a human sees the draft.

Deliberately re-derives the expected values from scratch (loader -> extract ->
aggregate -> placeholders) rather than trusting whatever value map injection
used, so a stale or tampered value map gets caught here too, not just a
drafting mistake. Flags two distinct failure modes: a number that should be
in the final document but isn't (wrong or missing value), and a placeholder
token that was never substituted at all (injection missed something).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from src.aggregate import aggregate
from src.extract import extract
from src.loader import load
from src.placeholders import placeholder_values

DEFAULT_DATA_DIR = Path(__file__).parent.parent / "data" / "clients"
PLACEHOLDER_RE = re.compile(r"\{\{[a-zA-Z0-9_.]+\}\}")


@dataclass
class CheckResult:
    ok: bool
    missing_values: list[str] = field(default_factory=list)
    leftover_placeholders: list[str] = field(default_factory=list)


def check(final_html: str, client_id: str, data_dir: Path = DEFAULT_DATA_DIR) -> CheckResult:
    docs_dir = data_dir / client_id / "raw_docs"
    records = [extract(load(p)) for p in sorted(docs_dir.glob("*.txt"))]
    summary = aggregate(records)
    expected = placeholder_values(records, summary)

    missing_values = [
        f"{name} = {value}" for name, value in sorted(expected.items())
        if value not in final_html
    ]
    leftover_placeholders = sorted(set(PLACEHOLDER_RE.findall(final_html)))

    return CheckResult(
        ok=not missing_values and not leftover_placeholders,
        missing_values=missing_values,
        leftover_placeholders=leftover_placeholders,
    )
