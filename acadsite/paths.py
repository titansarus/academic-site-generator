"""Filesystem boundary helpers used by configuration and content loaders."""

from __future__ import annotations

from pathlib import Path


class SitePathError(ValueError):
    """Raised when a configured path escapes its owning site directory."""


def resolve_within(root: str | Path, relative: str | Path, label: str = "Path") -> Path:
    """Resolve a relative path and require it to remain beneath ``root``.

    Resolving first also catches symlinks inside the site that point outside it.
    Site configuration is commonly version-controlled but may still come from
    an untrusted checkout, so it must not be able to publish arbitrary host
    files during a build.
    """
    root_path = Path(root).resolve()
    supplied = Path(str(relative))
    if supplied.is_absolute():
        raise SitePathError(f"{label} must be relative to the site directory: {relative}")
    candidate = (root_path / supplied).resolve()
    try:
        candidate.relative_to(root_path)
    except ValueError as exc:
        raise SitePathError(f"{label} escapes the site directory: {relative}") from exc
    return candidate
