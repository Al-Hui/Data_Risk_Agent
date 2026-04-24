from __future__ import annotations

import re
from collections.abc import Iterable


REFERENCE_PATTERN = re.compile(r"\b(?:OF|CT)-\d+\b", re.IGNORECASE)


def normalize_text(*parts: str) -> str:
    text = " ".join(parts).lower()
    return re.sub(r"\s+", " ", text).strip()


def extract_references(text: str) -> list[str]:
    return [match.upper() for match in REFERENCE_PATTERN.findall(text)]


def unique_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered

