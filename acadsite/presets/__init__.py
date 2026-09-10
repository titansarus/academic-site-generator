"""Preset discovery and loading.

A preset bundles default config fragments, JSON schemas, templates, and static
assets. Presets are packaged inside ``acadsite/presets/<name>/``. The engine
treats a preset as data: it reads ``preset.json`` for default config and knows
where to find the preset's templates and static assets for the override chain.
"""

from __future__ import annotations

import json
import re
from importlib import resources
from pathlib import Path
from typing import Any


class PresetError(Exception):
    """Raised when a preset is missing or malformed."""


_PRESET_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def preset_dir(name: str) -> Path:
    """Return the filesystem path to a packaged preset directory."""
    if not _PRESET_NAME_RE.fullmatch(str(name)):
        raise PresetError(f"Invalid preset name '{name}'.")
    base = resources.files("acadsite.presets") / name
    path = Path(str(base))
    if not path.is_dir():
        raise PresetError(f"Unknown preset '{name}' (looked in {path}).")
    return path


def load_preset_defaults(name: str) -> dict[str, Any]:
    """Load the ``defaults`` config block for a preset.

    Returns an empty dict when the preset defines no defaults. Missing presets
    other than the built-in fallbacks raise ``PresetError``.
    """
    try:
        pdir = preset_dir(name)
    except PresetError:
        if name in {"", "none", "base"}:
            return {}
        raise
    preset_file = pdir / "preset.json"
    if not preset_file.exists():
        return {}
    data = json.loads(preset_file.read_text(encoding="utf-8"))
    return data.get("defaults", {})


def preset_templates_path(name: str) -> Path | None:
    """Return the preset's templates directory if it exists."""
    try:
        path = preset_dir(name) / "templates"
    except PresetError:
        return None
    return path if path.is_dir() else None


def preset_static_path(name: str) -> Path | None:
    """Return the preset's static directory if it exists."""
    try:
        path = preset_dir(name) / "static"
    except PresetError:
        return None
    return path if path.is_dir() else None


def preset_schemas_path(name: str) -> Path | None:
    """Return the preset's schemas directory if it exists."""
    try:
        path = preset_dir(name) / "schemas"
    except PresetError:
        return None
    return path if path.is_dir() else None
