"""Scaffold a minimal working site (used by ``acadsite new``)."""

from __future__ import annotations

import json
from pathlib import Path

_CONFIG = {
    "preset": "academic",
    "features_file": "features.yml",
    "site": {"title": "New Site", "base_url": "", "base_path": "/"},
    "theme": {"default": "system", "accent": "blue"},
    "collections": {
        "notes": {
            "label": "Notes",
            "slug": "notes",
            "source": "content/notes.json",
            "type": "cards",
            "detail_pages": True,
        }
    },
    "homepage": {
        "sections": [
            {"type": "hero", "source": "content/profile.json"},
            {"type": "collection_preview", "title": "Notes", "collection": "notes", "limit": 3},
        ]
    },
    "pages": [{"title": "Notes", "slug": "notes", "layout": "collection_page", "collections": ["notes"]}],
}

_FEATURES = """# Global master switches. Set a value to false to hide it everywhere.
notes: true

# Academic preset presentation. Set false without removing logo data/assets.
organization_logos: true

# Homepage previews only.
homepage:
  notes: true

# Standalone pages and their automatically generated navigation links.
pages:
  notes: true
"""

_PROFILE = {
    "name": "Your Name",
    "tagline": "Your role",
    "affiliation": "Your affiliation",
    "about": "Write a short bio here in **Markdown**.",
    "research_interests": ["Topic one", "Topic two"],
    "links": [{"label": "Email", "url": "mailto:you@example.com", "glyph": "@"}],
}

_NOTES = [
    {"title": "First note", "summary": "A short summary.", "date": "2026-01-01",
     "body": "Hello from your first note."}
]


def scaffold_site(target: Path) -> None:
    if target.exists() and any(target.iterdir()):
        raise FileExistsError(f"{target} already exists and is not empty.")
    (target / "content").mkdir(parents=True, exist_ok=True)
    (target / "assets").mkdir(parents=True, exist_ok=True)
    (target / "site.config.json").write_text(json.dumps(_CONFIG, indent=2), encoding="utf-8")
    (target / "features.yml").write_text(_FEATURES, encoding="utf-8")
    (target / "content" / "profile.json").write_text(json.dumps(_PROFILE, indent=2), encoding="utf-8")
    (target / "content" / "notes.json").write_text(json.dumps(_NOTES, indent=2), encoding="utf-8")
