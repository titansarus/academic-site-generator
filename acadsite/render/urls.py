"""URL and output-path helpers.

All site-internal URLs are built relative to ``base_path`` so the same content
works at a domain root (``/``) or a project subpath (``/repo/``). Output paths
use ``<slug>/index.html`` so pages get clean, extensionless URLs.
"""

from __future__ import annotations

import re
from pathlib import Path


class UnsafeUrlError(ValueError):
    """Raised when a configured URL could escape the generated site tree."""


_DOMAIN_RE = re.compile(
    r"(?=.{1,253}\Z)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\Z"
)


def validate_custom_domain(value: str) -> str:
    """Validate the single hostname written to a GitHub Pages CNAME file."""
    domain = str(value).strip().lower()
    if not _DOMAIN_RE.fullmatch(domain):
        raise UnsafeUrlError(f"Invalid custom domain: {value!r}")
    return domain


def _validate_site_path(value: str, label: str) -> None:
    """Reject URL paths with filesystem/browser traversal semantics."""
    if any(ord(char) < 32 for char in value):
        raise UnsafeUrlError(f"{label} contains a control character.")
    if "\\" in value or "?" in value or "#" in value:
        raise UnsafeUrlError(f"{label} must be a plain URL path: {value!r}")
    if value.startswith("//"):
        raise UnsafeUrlError(f"{label} must not be a protocol-relative URL: {value!r}")
    if any(part in {".", ".."} for part in value.split("/")):
        raise UnsafeUrlError(f"{label} contains a traversal segment: {value!r}")
    for segment in value.strip("/").split("/"):
        if segment and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._~-]*", segment):
            raise UnsafeUrlError(f"{label} contains an unsafe segment: {value!r}")


class UrlBuilder:
    """Builds base-path-aware URLs and output file paths for one site."""

    def __init__(self, base_path: str):
        bp = base_path or "/"
        if not bp.startswith("/"):
            bp = "/" + bp
        if not bp.endswith("/"):
            bp += "/"
        _validate_site_path(bp, "Site base_path")
        self.base_path = bp

    def url(self, *parts: str) -> str:
        """Join path parts onto the base path into a site-absolute URL."""
        cleaned = []
        for part in parts:
            if part in (None, "", "/"):
                continue
            value = str(part).strip("/")
            _validate_site_path(value, "Route")
            cleaned.append(value)
        if not cleaned:
            return self.base_path
        return self.base_path + "/".join(cleaned) + "/"

    def asset(self, rel: str) -> str:
        """URL for a static asset, preserving its file extension."""
        value = str(rel).lstrip("/")
        _validate_site_path(value, "Asset URL")
        return self.base_path + value

    def absolute(self, base_url: str, rel_url: str) -> str:
        """Combine a site ``base_url`` with a site-absolute path."""
        return base_url.rstrip("/") + rel_url

    @staticmethod
    def output_path(output_root: Path, rel_url: str) -> Path:
        """Map a site-absolute URL to a file path under ``output_root``.

        ``/`` -> ``index.html``; ``/foo/`` -> ``foo/index.html``.
        """
        rel = rel_url.strip("/")
        candidate = output_root / "index.html" if not rel else output_root / rel / "index.html"
        root = output_root.resolve()
        resolved = candidate.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise UnsafeUrlError(
                f"Generated route escapes the output directory: {rel_url!r}"
            ) from exc
        return resolved
