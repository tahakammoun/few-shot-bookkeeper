"""Substitutes real values into a model-drafted HTML report.

Pure string replacement — every {{token.name}} in the draft is swapped for
its value from placeholders.py. No arithmetic happens here; all of it
already happened deterministically upstream (extract.py / aggregate.py).
"""

from __future__ import annotations

import re

PLACEHOLDER_RE = re.compile(r"\{\{([a-zA-Z0-9_.]+)\}\}")


class MissingPlaceholderError(Exception):
    """Raised when the draft references a token with no known value — the
    drafter invented a name outside the required schema, or the schema
    changed and the draft is stale."""


def inject(draft_html: str, values: dict[str, str]) -> str:
    def replace(match: re.Match) -> str:
        token = match.group(1)
        if token not in values:
            raise MissingPlaceholderError(token)
        return values[token]

    return PLACEHOLDER_RE.sub(replace, draft_html)
