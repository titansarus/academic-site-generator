"""Generic content loading and shaping.

Collections are lists of structured items loaded from JSON or YAML. Item body
Markdown may be inlined or referenced from a file. Loading also applies generic
sorting, grouping, filtering, and slug assignment. None of this is
academic-specific: publications and hobbies flow through the same code path.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import dates
from .config import CollectionConfig, Site
from .markdown import render_inline, render_markdown


class ContentError(Exception):
    """Raised when content cannot be loaded or is malformed."""


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """Turn an arbitrary string into a URL-friendly slug."""
    slug = _SLUG_RE.sub("-", str(value).strip().lower()).strip("-")
    return slug or "item"


def _load_structured(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        import yaml

        return yaml.safe_load(text)
    return json.loads(text)


@dataclass
class Collection:
    """A loaded, shaped collection ready for rendering."""

    config: CollectionConfig
    items: list[dict]
    groups: list[dict] = field(default_factory=list)

    @property
    def key(self) -> str:
        return self.config.key

    @property
    def label(self) -> str:
        return self.config.label

    @property
    def slug(self) -> str:
        return self.config.slug

    @property
    def type(self) -> str:
        return self.config.type


def load_collection(site: Site, config: CollectionConfig) -> Collection:
    """Load and shape a single collection from its configured source."""
    if not config.source:
        return Collection(config=config, items=[])

    source_path = (site.root / config.source).resolve()
    if not source_path.exists():
        raise ContentError(
            f"Collection '{config.key}' source not found: {config.source}"
        )

    data = _load_structured(source_path)
    if isinstance(data, dict) and "items" in data:
        data = data["items"]
    if not isinstance(data, list):
        raise ContentError(
            f"Collection '{config.key}' source must be a list (or an object with "
            f"an 'items' list); got {type(data).__name__}."
        )

    items = [
        _normalize_item(site, config, raw, index)
        for index, raw in enumerate(data)
    ]
    items = [it for it in items if not it.get("draft")]
    items = _sort_items(items, config)
    groups = _group_items(items, config)
    return Collection(config=config, items=items, groups=groups)


def _normalize_item(
    site: Site, config: CollectionConfig, raw: dict, index: int
) -> dict:
    """Copy and enrich a raw item with derived, render-ready fields."""
    if not isinstance(raw, dict):
        raise ContentError(
            f"Every item in collection '{config.key}' must be a mapping; "
            f"item #{index} is {type(raw).__name__}."
        )
    item = dict(raw)

    title = item.get("title", "")
    item.setdefault("slug", slugify(title) if title else f"item-{index + 1}")
    item["_index"] = index
    item["_collection"] = config.key

    # Body Markdown: either an inline string, or a path to a .md file.
    body_html = ""
    body = item.get("body")
    if body:
        candidate = site.root / body
        if isinstance(body, str) and (body.endswith(".md") or candidate.exists()):
            if candidate.exists():
                body_html = render_markdown(candidate.read_text(encoding="utf-8"))
                item["_body_source"] = body
            else:
                item.setdefault("_missing_body", body)
        else:
            body_html = render_markdown(str(body))
    item["body_html"] = body_html

    if item.get("summary"):
        item["summary_html"] = render_inline(str(item["summary"]))
    else:
        item["summary_html"] = ""

    item["display_date"] = dates.display_date(item)
    item.setdefault("tags", [])
    item.setdefault("links", [])

    # Detail-page URL is filled in later by the engine when detail_pages is on.
    item.setdefault("url", None)
    return item


def _sort_items(items: list[dict], config: CollectionConfig) -> list[dict]:
    """Sort items by the configured field, honoring manual ``order``."""
    if config.sort_by:
        reverse = config.sort_order.lower() != "asc"
        items = sorted(
            items, key=lambda it: dates.sort_key(it, config.sort_by), reverse=reverse
        )
    # Manual order always takes precedence when present.
    if any("order" in it for it in items):
        items = sorted(items, key=lambda it: it.get("order", 10**6))
    return items


def _group_items(items: list[dict], config: CollectionConfig) -> list[dict]:
    """Group items by a field into ordered ``{category, items}`` buckets."""
    if not config.group_by:
        return []
    order: list[str] = []
    buckets: dict[str, list[dict]] = {}
    for item in items:
        category = item.get(config.group_by) or "Other"
        if category not in buckets:
            buckets[category] = []
            order.append(category)
        buckets[category].append(item)
    return [{"category": cat, "items": buckets[cat]} for cat in order]


def apply_filter(items: list[dict], flt: dict | None) -> list[dict]:
    """Filter items by an equality map, e.g. ``{"featured": true}``."""
    if not flt:
        return items
    result = []
    for item in items:
        if all(item.get(key) == value for key, value in flt.items()):
            result.append(item)
    return result
