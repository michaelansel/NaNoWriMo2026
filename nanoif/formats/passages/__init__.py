"""Passage index page (``passages.html``): every passage with its file, links and size."""

from nanoif.formats.passages.generator import (
    LooseEnd,
    PassageRow,
    PassagesResult,
    build_passages,
    loose_ends,
    passage_rows,
)

__all__ = [
    "LooseEnd",
    "PassageRow",
    "PassagesResult",
    "build_passages",
    "loose_ends",
    "passage_rows",
]
