"""The build engine.

Generic renderers only: ``render_page``, ``render_collection``,
``render_homepage``, ``render_detail_page``. There are deliberately no
per-topic functions like ``render_experience_page``. Page shape comes from the
``layout`` name (a template) and the collections/sections referenced in config.
"""

from __future__ import annotations

import json
import shutil
from datetime import date, datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PackageLoader, select_autoescape

from .. import presets
from ..bibtex import generate_bibtex
from ..config import PageConfig, Site
from ..content import Collection, apply_filter, load_collection
from ..markdown import render_inline, render_markdown
from .assets import copy_static_assets
from .urls import UrlBuilder


class BuildResult:
    """Summary of a build for CLI reporting."""

    def __init__(self) -> None:
        self.pages: list[str] = []
        self.warnings: list[str] = []

    def add_page(self, rel_url: str) -> None:
        self.pages.append(rel_url)


class Engine:
    """Renders a fully-resolved :class:`Site` into a static site tree."""

    def __init__(self, site: Site, verbose: bool = False):
        self.site = site
        self.verbose = verbose
        self.urls = UrlBuilder(site.base_path)
        self.env = self._build_environment()
        self.collections: dict[str, Collection] = {}
        self.result = BuildResult()

    # -- environment -----------------------------------------------------
    def _build_environment(self) -> Environment:
        loaders = []
        site_templates = self.site.root / "templates"
        if site_templates.is_dir():
            loaders.append(FileSystemLoader(str(site_templates)))
        preset_templates = presets.preset_templates_path(self.site.preset_name)
        if preset_templates and preset_templates.is_dir():
            loaders.append(
                PackageLoader("acadsite", f"presets/{self.site.preset_name}/templates")
            )
        loaders.append(PackageLoader("acadsite", "templates/core"))

        env = Environment(
            loader=ChoiceLoader(loaders),
            autoescape=select_autoescape(["html", "xml", "j2"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        env.filters["markdown"] = render_markdown
        env.filters["inline_markdown"] = render_inline
        env.filters["media_url"] = self.media_url
        env.globals["url"] = self.urls.url
        env.globals["asset"] = self.urls.asset
        env.globals["media_url"] = self.media_url
        env.globals["bibtex"] = generate_bibtex
        env.globals["now_year"] = date.today().year
        return env

    def media_url(self, path: str | None) -> str:
        """Resolve a content-supplied media path to a usable URL."""
        if not path:
            return ""
        text = str(path)
        if text.startswith(("http://", "https://", "//", "mailto:", "data:")):
            return text
        return self.urls.base_path + text.lstrip("/")

    # -- loading ---------------------------------------------------------
    def load(self) -> None:
        """Load all collections and assign detail-page URLs."""
        for key, config in self.site.collections.items():
            collection = load_collection(self.site, config)
            if config.detail_pages:
                for item in collection.items:
                    item["url"] = self.urls.url(config.slug, item["slug"])
            self.collections[key] = collection

    # -- context ---------------------------------------------------------
    def base_context(self, page_slug: str = "") -> dict:
        nav = []
        for entry in self.site.nav:
            href = entry.get("href") or self.urls.url(entry.get("slug", ""))
            nav.append(
                {
                    "label": entry["label"],
                    "href": href,
                    "active": entry.get("slug", "") == page_slug,
                }
            )
        return {
            "site": self.site.site,
            "theme": self.site.theme,
            "nav": nav,
            "base_path": self.site.base_path,
            "config": self.site.data,
            "math_enabled": bool(self.site.data.get("math")),
            "current_slug": page_slug,
        }

    # -- rendering primitives -------------------------------------------
    def _render_to(self, template_name: str, rel_url: str, context: dict, output_root: Path) -> None:
        template = self.env.get_template(template_name)
        html = template.render(**context)
        out_path = UrlBuilder.output_path(output_root, rel_url)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
        self.result.add_page(rel_url)

    # -- homepage --------------------------------------------------------
    def render_homepage(self, output_root: Path) -> None:
        sections = [self._resolve_section(s) for s in self.site.homepage.get("sections", [])]
        context = self.base_context("")
        context.update({"page": {"title": self.site.title, "slug": ""}, "sections": sections})
        self._render_to("layouts/homepage.html.j2", "/", context, output_root)

    def _resolve_section(self, section: dict) -> dict:
        stype = section.get("type")
        resolved = dict(section)
        if stype == "hero":
            resolved["profile"] = self._load_profile(section.get("source"))
        elif stype == "collection_preview":
            key = section.get("collection")
            collection = self.collections.get(key)
            if collection is None:
                resolved["items"] = []
                resolved["groups"] = []
                resolved["missing"] = key
                return resolved
            items = apply_filter(collection.items, section.get("filter"))
            limit = section.get("limit")
            preview_items = items[:limit] if limit else items
            resolved.update(
                {
                    "collection": collection,
                    "collection_key": key,
                    "items": preview_items,
                    "all_items": items,
                    "groups": collection.groups,
                    "full_url": self.urls.url(collection.slug),
                    "has_more": bool(limit) and len(items) > limit,
                }
            )
        elif stype == "markdown":
            resolved["html"] = self._load_markdown_section(section)
        elif stype == "news" or stype == "list":
            resolved["items"] = self._load_list(section.get("source"))
        return resolved

    def _load_profile(self, source: str | None) -> dict:
        if not source:
            return {}
        path = self.site.root / source
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("about"):
            data["about_html"] = render_markdown(str(data["about"]))
        if data.get("bio"):
            data["bio_html"] = render_markdown(str(data["bio"]))
        return data

    def _load_markdown_section(self, section: dict) -> str:
        if section.get("body"):
            path = self.site.root / section["body"]
            if path.exists():
                return render_markdown(path.read_text(encoding="utf-8"))
        if section.get("content"):
            return render_markdown(str(section["content"]))
        return ""

    def _load_list(self, source: str | None) -> list[dict]:
        if not source:
            return []
        path = self.site.root / source
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "items" in data:
            data = data["items"]
        return data if isinstance(data, list) else []

    # -- pages -----------------------------------------------------------
    def render_page(self, page: PageConfig, output_root: Path) -> None:
        cols = [self.collections[k] for k in page.collections if k in self.collections]
        context = self.base_context(page.slug)
        rel_url = self.urls.url(page.slug) if page.slug else "/"

        body_html = ""
        if page.body:
            body_path = self.site.root / page.body
            if body_path.exists():
                body_html = render_markdown(body_path.read_text(encoding="utf-8"))

        context.update(
            {
                "page": {"title": page.title, "slug": page.slug, "layout": page.layout},
                "collections": cols,
                "collection": cols[0] if cols else None,
                "body_html": body_html,
            }
        )
        template_name = f"layouts/{page.layout}.html.j2"
        self._render_to(template_name, rel_url, context, output_root)

    def render_detail_pages(self, output_root: Path) -> None:
        for key, collection in self.collections.items():
            if not collection.config.detail_pages:
                continue
            for item in collection.items:
                context = self.base_context(collection.slug)
                context.update(
                    {
                        "page": {"title": item.get("title", ""), "slug": item["slug"]},
                        "collection": collection,
                        "item": item,
                    }
                )
                rel_url = self.urls.url(collection.slug, item["slug"])
                template_name = f"layouts/{collection.config.detail_layout}.html.j2"
                self._render_to(template_name, rel_url, context, output_root)

    # -- special outputs -------------------------------------------------
    def render_404(self, output_root: Path) -> None:
        context = self.base_context("404")
        context.update({"page": {"title": "Page not found", "slug": "404"}})
        (output_root / "404.html").write_text(
            self.env.get_template("layouts/not_found.html.j2").render(**context),
            encoding="utf-8",
        )
        self.result.pages.append("/404.html")

    def write_sitemap(self, output_root: Path) -> None:
        base = self.site.base_url or ""
        urls = []
        seen = set()
        for rel in self.result.pages:
            if rel.endswith(".html") and rel != "/404.html":
                continue
            if rel in seen:
                continue
            seen.add(rel)
            loc = escape(base + rel) if base else escape(rel)
            urls.append(f"  <url><loc>{loc}</loc></url>")
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(urls)
            + "\n</urlset>\n"
        )
        (output_root / "sitemap.xml").write_text(xml, encoding="utf-8")

    def write_feed(self, output_root: Path) -> None:
        feed_cfg = self.site.data.get("feed")
        if not feed_cfg or not feed_cfg.get("enabled"):
            return
        key = feed_cfg.get("collection")
        collection = self.collections.get(key)
        if collection is None:
            return
        base = self.site.base_url or ""
        title = escape(feed_cfg.get("title", self.site.title))
        self_url = escape(base + self.urls.asset("feed.xml"))
        updated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        entries = []
        for item in collection.items[: feed_cfg.get("limit", 20)]:
            item_url = escape(base + (item.get("url") or self.urls.url(collection.slug, item["slug"])))
            summary = escape(item.get("summary", "") or "")
            entries.append(
                "  <entry>\n"
                f"    <title>{escape(item.get('title', ''))}</title>\n"
                f"    <link href=\"{item_url}\"/>\n"
                f"    <id>{item_url}</id>\n"
                f"    <updated>{updated}</updated>\n"
                f"    <summary>{summary}</summary>\n"
                "  </entry>"
            )
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<feed xmlns="http://www.w3.org/2005/Atom">\n'
            f"  <title>{title}</title>\n"
            f"  <link href=\"{self_url}\" rel=\"self\"/>\n"
            f"  <updated>{updated}</updated>\n"
            f"  <id>{escape(base + self.site.base_path)}</id>\n"
            + "\n".join(entries)
            + "\n</feed>\n"
        )
        (output_root / "feed.xml").write_text(xml, encoding="utf-8")

    def write_cname(self, output_root: Path) -> None:
        domain = self.site.custom_domain
        if domain:
            (output_root / "CNAME").write_text(domain + "\n", encoding="utf-8")

    # -- top-level build -------------------------------------------------
    def build(self, output: str | Path, clean: bool = True) -> BuildResult:
        output_root = Path(output).resolve()
        if clean and output_root.exists():
            shutil.rmtree(output_root)
        output_root.mkdir(parents=True, exist_ok=True)

        self.load()
        self.render_homepage(output_root)
        for page in self.site.pages:
            self.render_page(page, output_root)
        self.render_detail_pages(output_root)
        self.render_404(output_root)

        self.result.warnings += copy_static_assets(self.site, output_root, self.verbose)
        self.write_sitemap(output_root)
        self.write_feed(output_root)
        self.write_cname(output_root)
        return self.result


def build_site(site: Site, output: str | Path, verbose: bool = False, clean: bool = True) -> BuildResult:
    """Convenience wrapper: construct an :class:`Engine` and build."""
    engine = Engine(site, verbose=verbose)
    return engine.build(output, clean=clean)
