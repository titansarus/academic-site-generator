"""Minimal BibTeX support for publication-style items.

If an item already carries a ``bibtex`` string it is used as-is. Otherwise a
best-effort entry is synthesized from common fields. This is intentionally
simple -- it is a convenience, not a full BibTeX engine.
"""

from __future__ import annotations

import re


def _cite_key(item: dict) -> str:
    authors = item.get("authors", "")
    first_surname = ""
    if authors:
        first_author = re.split(r",| and ", str(authors))[0].strip()
        parts = first_author.split()
        first_surname = parts[-1] if parts else ""
    year = str(item.get("year", "") or "")
    title_word = ""
    for word in re.findall(r"[A-Za-z]+", str(item.get("title", ""))):
        if len(word) > 3:
            title_word = word.lower()
            break
    key = f"{first_surname.lower()}{year}{title_word}"
    key = re.sub(r"[^a-z0-9]", "", key)
    return key or "ref"


def generate_bibtex(item: dict) -> str:
    """Return a BibTeX entry for a publication item (given or synthesized)."""
    if item.get("bibtex"):
        return str(item["bibtex"])

    entry_type = item.get("entry_type") or (
        "inproceedings" if item.get("venue") else "article"
    )
    fields: list[tuple[str, str]] = []
    if item.get("title"):
        fields.append(("title", str(item["title"])))
    if item.get("authors"):
        authors = re.sub(r"\s*,\s*", " and ", str(item["authors"]))
        fields.append(("author", authors))
    if item.get("venue"):
        key = "booktitle" if entry_type == "inproceedings" else "journal"
        fields.append((key, str(item["venue"])))
    if item.get("year"):
        fields.append(("year", str(item["year"])))
    if item.get("doi"):
        fields.append(("doi", str(item["doi"])))

    lines = [f"@{entry_type}{{{_cite_key(item)},"]
    for name, value in fields:
        lines.append(f"  {name}={{{value}}},")
    if len(lines) > 1:
        lines[-1] = lines[-1].rstrip(",")
    lines.append("}")
    return "\n".join(lines)
