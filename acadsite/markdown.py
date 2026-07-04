"""Markdown rendering.

Thin wrapper around python-markdown with a stable extension set. Math is left
untouched so a client-side math renderer (e.g. MathJax, enabled via config) can
process ``$...$`` / ``$$...$$`` delimiters after page load.
"""

from __future__ import annotations

from functools import lru_cache

_EXTENSIONS = [
    "extra",
    "sane_lists",
    "smarty",
    "tables",
    "fenced_code",
    "toc",
]


@lru_cache(maxsize=1)
def _make_md():
    import markdown as md

    return md.Markdown(extensions=_EXTENSIONS, output_format="html5")


def render_markdown(text: str | None) -> str:
    """Render a Markdown string to an HTML fragment."""
    if not text:
        return ""
    converter = _make_md()
    converter.reset()
    return converter.convert(text)


def render_inline(text: str | None) -> str:
    """Render Markdown but strip the wrapping <p> for single-line summaries."""
    html = render_markdown(text).strip()
    if html.startswith("<p>") and html.endswith("</p>") and html.count("<p>") == 1:
        html = html[3:-4]
    return html
