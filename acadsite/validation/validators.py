"""Site and content validation.

Validation is generic and preset-schema aware. It reports hard ``errors`` that
should block a build and soft ``warnings`` that are safe to ignore. It checks
config integrity (duplicate slugs, missing sources, dangling collection/page
references), item shape against optional preset schemas, and missing body files.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import presets
from ..config import Site
from ..content import ContentError, load_collection
from ..paths import SitePathError, resolve_within
from ..render.urls import UnsafeUrlError, UrlBuilder, validate_custom_domain


class ValidationReport:
    """Collects errors and warnings from a validation pass."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    @property
    def ok(self) -> bool:
        return not self.errors


def _load_schema(preset_name: str, schema_name: str) -> dict | None:
    schemas_dir = presets.preset_schemas_path(preset_name)
    if not schemas_dir:
        return None
    path = resolve_within(
        schemas_dir,
        f"{schema_name}.schema.json",
        f"Schema '{schema_name}'",
    )
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_item_schema(item: dict, schema: dict, ctx: str, report: ValidationReport) -> None:
    for field_name in schema.get("required", []):
        if field_name not in item or item[field_name] in (None, ""):
            report.error(f"{ctx}: missing required field '{field_name}'.")
    known = set(schema.get("properties", {}).keys())
    if known and not schema.get("additionalProperties", True):
        for key in item:
            if key.startswith("_"):
                continue
            if key not in known:
                report.warn(f"{ctx}: unknown field '{key}'.")


def validate_site(site: Site) -> ValidationReport:
    """Validate a fully-resolved site config plus its content."""
    report = ValidationReport()

    try:
        urls = UrlBuilder(site.base_path)
    except UnsafeUrlError as exc:
        report.error(str(exc))
        urls = None

    for directory_name in ("templates", "static", "assets"):
        raw_directory = site.root / directory_name
        if not raw_directory.exists() and not raw_directory.is_symlink():
            continue
        try:
            resolve_within(
                site.root,
                directory_name,
                f"Site {directory_name} directory",
            )
        except SitePathError as exc:
            report.error(str(exc))

    if site.custom_domain:
        try:
            validate_custom_domain(site.custom_domain)
        except UnsafeUrlError as exc:
            report.error(str(exc))

    # Duplicate collection slugs.
    slug_seen: dict[str, str] = {}
    for key, cfg in site.collections.items():
        if urls:
            try:
                urls.url(cfg.slug)
            except UnsafeUrlError as exc:
                report.error(f"Collection '{key}': {exc}")
        if cfg.slug in slug_seen:
            report.error(
                f"Duplicate collection slug '{cfg.slug}' used by "
                f"'{slug_seen[cfg.slug]}' and '{key}'."
            )
        slug_seen[cfg.slug] = key

    # Duplicate page slugs.
    page_slug_seen: dict[str, bool] = {}
    for page in site.pages:
        if urls:
            try:
                urls.url(page.slug)
            except UnsafeUrlError as exc:
                report.error(f"Page '{page.title}': {exc}")
        if page.slug in page_slug_seen:
            report.error(f"Duplicate page slug '{page.slug}'.")
        page_slug_seen[page.slug] = True
        for col_key in page.collections:
            if col_key not in site.collections:
                report.error(
                    f"Page '{page.slug}' references unknown collection '{col_key}'."
                )
        if page.body:
            try:
                page_body = resolve_within(site.root, page.body, f"Page '{page.slug}' body")
                if not page_body.exists():
                    report.warn(f"Page '{page.slug}' body file not found: {page.body}")
            except SitePathError as exc:
                report.error(str(exc))

    # Homepage section references.
    for section in site.homepage.get("sections", []):
        stype = section.get("type")
        if stype == "collection_preview":
            key = section.get("collection")
            if key not in site.collections:
                report.error(
                    f"Homepage collection_preview references unknown collection '{key}'."
                )
        source = section.get("source") or section.get("body")
        if source:
            try:
                section_source = resolve_within(site.root, source, "Homepage section source")
                if not section_source.exists():
                    report.warn(f"Homepage section source not found: {source}")
            except SitePathError as exc:
                report.error(str(exc))

    # Content: sources exist, schemas satisfied, body files present.
    for key, cfg in site.collections.items():
        if not cfg.source:
            report.warn(f"Collection '{key}' has no source; it will be empty.")
            continue
        try:
            source_path = resolve_within(
                site.root, cfg.source, f"Collection '{key}' source"
            )
        except SitePathError as exc:
            report.error(str(exc))
            continue
        if not source_path.exists():
            report.error(f"Collection '{key}' source not found: {cfg.source}")
            continue
        try:
            collection = load_collection(site, cfg)
        except ContentError as exc:
            report.error(str(exc))
            continue

        try:
            schema = _load_schema(site.preset_name, cfg.schema) if cfg.schema else None
        except SitePathError as exc:
            report.error(f"Collection '{key}': {exc}")
            schema = None
        item_slugs: dict[str, bool] = {}
        for item in collection.items:
            ctx = f"Collection '{key}' item '{item.get('title', item.get('slug'))}'"
            if schema:
                _validate_item_schema(item, schema, ctx, report)
            slug = item.get("slug")
            if urls and cfg.detail_pages:
                try:
                    urls.url(cfg.slug, slug)
                except UnsafeUrlError as exc:
                    report.error(f"{ctx}: {exc}")
            if slug in item_slugs and cfg.detail_pages:
                report.error(f"{ctx}: duplicate slug '{slug}' within collection.")
            item_slugs[slug] = True
            if item.get("_missing_body"):
                report.warn(f"{ctx}: body file not found: {item['_missing_body']}")

    return report
