"""URL and output-path helpers.

All site-internal URLs are built relative to ``base_path`` so the same content
works at a domain root (``/``) or a project subpath (``/repo/``). Output paths
use ``<slug>/index.html`` so pages get clean, extensionless URLs.
"""

from __future__ import annotations

from pathlib import Path


class UrlBuilder:
    """Builds base-path-aware URLs and output file paths for one site."""

    def __init__(self, base_path: str):
        bp = base_path or "/"
        if not bp.startswith("/"):
            bp = "/" + bp
        if not bp.endswith("/"):
            bp += "/"
        self.base_path = bp

    def url(self, *parts: str) -> str:
        """Join path parts onto the base path into a site-absolute URL."""
        cleaned = [str(p).strip("/") for p in parts if p not in (None, "", "/")]
        if not cleaned:
            return self.base_path
        return self.base_path + "/".join(cleaned) + "/"

    def asset(self, rel: str) -> str:
        """URL for a static asset, preserving its file extension."""
        return self.base_path + str(rel).lstrip("/")

    def absolute(self, base_url: str, rel_url: str) -> str:
        """Combine a site ``base_url`` with a site-absolute path."""
        return base_url.rstrip("/") + rel_url

    @staticmethod
    def output_path(output_root: Path, rel_url: str) -> Path:
        """Map a site-absolute URL to a file path under ``output_root``.

        ``/`` -> ``index.html``; ``/foo/`` -> ``foo/index.html``.
        """
        rel = rel_url.strip("/")
        if not rel:
            return output_root / "index.html"
        return output_root / rel / "index.html"
