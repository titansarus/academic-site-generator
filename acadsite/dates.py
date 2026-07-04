"""Date parsing and display helpers.

Supported input formats: ``YYYY``, ``YYYY-MM``, ``YYYY-MM-DD``. A
``display_date`` field always overrides auto-formatting. Items without any date
sort after dated items unless a manual ``order`` is given.
"""

from __future__ import annotations

from datetime import date

_MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def parse_date(value) -> date | None:
    """Parse a partial date string into a ``date`` (missing parts -> 1)."""
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    text = str(value).strip()
    parts = text.split("-")
    try:
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        day = int(parts[2]) if len(parts) > 2 else 1
        return date(year, month, day)
    except (ValueError, IndexError):
        return None


def _precision(value) -> int:
    """Return how many date components were supplied (1=year..3=day)."""
    if value is None or value == "":
        return 0
    return min(len(str(value).split("-")), 3)


def format_date(value) -> str:
    """Format a single date at its input precision (e.g. ``Aug 2026``)."""
    parsed = parse_date(value)
    if parsed is None:
        return ""
    precision = _precision(value)
    if precision <= 1:
        return str(parsed.year)
    if precision == 2:
        return f"{_MONTHS[parsed.month - 1]} {parsed.year}"
    return f"{_MONTHS[parsed.month - 1]} {parsed.day}, {parsed.year}"


def display_date(item: dict) -> str:
    """Compute the human-facing date string for a content item.

    Precedence: explicit ``display_date`` -> start/end range -> single ``date``.
    ``current: true`` with no ``end_date`` renders as ``Present``.
    """
    if item.get("display_date"):
        return str(item["display_date"])

    start = item.get("start_date")
    end = item.get("end_date")
    if start or end:
        start_txt = format_date(start) if start else ""
        if item.get("current") and not end:
            end_txt = "Present"
        else:
            end_txt = format_date(end) if end else ""
        if start_txt and end_txt:
            return f"{start_txt} – {end_txt}"
        return start_txt or end_txt

    if item.get("date"):
        return format_date(item["date"])
    return ""


def sort_key(item: dict, field: str):
    """Build a sort key that pushes undated items to the end.

    Returns ``(has_value, date_or_number)`` so that items with a value always
    sort ahead of those without, regardless of ascending/descending order.
    """
    raw = item.get(field)
    if raw is None or raw == "":
        return (0, date.min)
    parsed = parse_date(raw)
    if parsed is not None:
        return (1, parsed)
    try:
        return (1, date(int(raw), 1, 1))
    except (ValueError, TypeError):
        return (1, date.min)
