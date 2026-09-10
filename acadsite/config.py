"""Site configuration loading and resolution.

Config is generic. It is loaded from JSON or YAML, deep-merged with the
selected preset defaults and an optional environment overlay, then exposed as
lightweight dataclasses. Nothing here knows about publications, experience,
or any other academic concept -- those are just keys in ``collections`` and
``pages`` supplied by the site or the preset.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import presets
from .paths import SitePathError, resolve_within


class ConfigError(Exception):
    """Raised when a site configuration cannot be loaded or resolved."""


def _load_structured(path: Path) -> Any:
    """Load a JSON or YAML file based on its suffix."""
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover - optional dep guard
            raise ConfigError(
                f"YAML file {path} requires PyYAML. Install with 'pip install pyyaml'."
            ) from exc
        return yaml.safe_load(text)
    return json.loads(text)


def deep_merge(base: dict, overlay: dict) -> dict:
    """Recursively merge ``overlay`` into a copy of ``base``.

    Dicts merge key-by-key; every other type (including lists) is replaced.
    """
    result = copy.deepcopy(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _load_features(site_dir: Path, merged: dict) -> dict[str, Any]:
    """Load optional feature flags shared by pages, collections, and sections."""
    features: dict = {}
    feature_file = merged.get("features_file")
    if feature_file:
        try:
            path = resolve_within(site_dir, str(feature_file), "Features file")
        except SitePathError as exc:
            raise ConfigError(str(exc)) from exc
        if not path.exists():
            raise ConfigError(f"Features file not found: {path}")
        loaded = _load_structured(path)
        if not isinstance(loaded, dict):
            raise ConfigError(f"Features file {path} must be a mapping of names to booleans.")
        features = loaded

    inline = merged.get("features", {})
    if not isinstance(inline, dict):
        raise ConfigError("Config field 'features' must be a mapping of names to booleans.")
    features = deep_merge(features, inline)
    for key, value in features.items():
        if isinstance(value, dict):
            for nested_key, nested_value in value.items():
                if not isinstance(nested_value, bool):
                    raise ConfigError(
                        f"Feature '{key}.{nested_key}' must be true or false, "
                        f"not {nested_value!r}."
                    )
        elif not isinstance(value, bool):
            raise ConfigError(f"Feature '{key}' must be true or false, not {value!r}.")
    return features


def _enabled(
    data: dict, key: str, features: dict[str, Any], scope: str | None = None
) -> bool:
    """Resolve an item's local ``enabled`` switch and optional feature key."""
    feature_key = data.get("feature", key)
    global_value = features.get(feature_key, True)
    if not isinstance(global_value, bool):
        global_value = True
    scoped_values = features.get(scope, {}) if scope else {}
    scoped_value = scoped_values.get(feature_key, True) if isinstance(scoped_values, dict) else True
    return bool(data.get("enabled", True)) and global_value and scoped_value


def _page_feature_key(page: dict) -> str:
    """Use a page's collection key when possible so flags stay consistent."""
    collections = page.get("collections", [])
    return page.get("feature") or (collections[0] if collections else page.get("slug", ""))


def _homepage_section_enabled(
    section: dict, features: dict[str, Any], disabled_collections: set[str]
) -> bool:
    """Gate previews by collection while keeping heroes with optional collections."""
    is_preview = section.get("type") == "collection_preview"
    key = section.get("collection") if is_preview else section.get("type", "section")
    return _enabled(section, key, features, scope="homepage") and not (
        is_preview and section.get("collection") in disabled_collections
    )


def find_config_file(site_dir: Path) -> Path:
    """Locate the site config file inside ``site_dir``."""
    candidates = [
        "site.config.json",
        "site.config.yaml",
        "site.config.yml",
        "site.json",
        "config.json",
    ]
    for name in candidates:
        try:
            candidate = resolve_within(site_dir, name, "Config file")
        except SitePathError as exc:  # defensive: the candidate names are fixed
            raise ConfigError(str(exc)) from exc
        if candidate.exists():
            return candidate
    raise ConfigError(
        f"No site config found in {site_dir}. Expected one of: {', '.join(candidates)}"
    )


@dataclass
class CollectionConfig:
    """Configuration for one generic collection."""

    key: str
    raw: dict
    label: str = ""
    slug: str = ""
    source: str = ""
    type: str = "cards"
    schema: str | None = None
    item_component: str | None = None
    sort_by: str | None = None
    sort_order: str = "desc"
    group_by: str | None = None
    detail_pages: bool = False
    detail_layout: str = "detail_page"

    @classmethod
    def from_dict(cls, key: str, data: dict) -> "CollectionConfig":
        return cls(
            key=key,
            raw=data,
            label=data.get("label", key.replace("_", " ").title()),
            slug=data.get("slug", key.replace("_", "-")),
            source=data.get("source", ""),
            type=data.get("type", "cards"),
            schema=data.get("schema"),
            item_component=data.get("item_component"),
            sort_by=data.get("sort_by"),
            sort_order=data.get("sort_order", "desc"),
            group_by=data.get("group_by"),
            detail_pages=bool(data.get("detail_pages", False)),
            detail_layout=data.get("detail_layout", "detail_page"),
        )


@dataclass
class PageConfig:
    """Configuration for one output page/route."""

    title: str
    slug: str
    raw: dict
    layout: str = "collection_page"
    collections: list[str] = field(default_factory=list)
    body: str | None = None
    nav: bool = True
    output: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "PageConfig":
        return cls(
            title=data.get("title", data.get("slug", "Page").title()),
            slug=data.get("slug", ""),
            raw=data,
            layout=data.get("layout", "collection_page"),
            collections=list(data.get("collections", [])),
            body=data.get("body"),
            nav=bool(data.get("nav", True)),
            output=data.get("output"),
        )


@dataclass
class Site:
    """Fully resolved site configuration."""

    root: Path
    data: dict
    preset_name: str
    site: dict
    theme: dict
    collections: dict[str, CollectionConfig]
    pages: list[PageConfig]
    homepage: dict
    nav: list[dict]

    @property
    def title(self) -> str:
        return self.site.get("title", "Website")

    @property
    def base_path(self) -> str:
        bp = self.site.get("base_path", "/")
        if not bp.startswith("/"):
            bp = "/" + bp
        if not bp.endswith("/"):
            bp += "/"
        return bp

    @property
    def base_url(self) -> str:
        return self.site.get("base_url", "").rstrip("/")

    @property
    def custom_domain(self) -> str | None:
        domain = self.site.get("custom_domain")
        return domain or None


def load_site(
    site_dir: str | Path, env: str | None = None, config_filename: str | None = None
) -> Site:
    """Load and fully resolve a site configuration.

    Resolution order (deep-merged, later wins):
    1. preset defaults (``presets/<name>/preset.json`` ``defaults`` block)
    2. the site config file
    3. ``environments[env]`` overlay from the merged config, if requested

    ``config_filename`` selects an alternate config file inside ``site_dir``
    (e.g. a second theme that shares the same content), instead of the
    auto-detected ``site.config.json``.
    """
    site_dir = Path(site_dir).resolve()
    if config_filename:
        try:
            config_path = resolve_within(site_dir, config_filename, "Config file")
        except SitePathError as exc:
            raise ConfigError(str(exc)) from exc
        if not config_path.exists():
            raise ConfigError(f"Config file not found: {config_path}")
    else:
        config_path = find_config_file(site_dir)
    raw = _load_structured(config_path)
    if not isinstance(raw, dict):
        raise ConfigError(f"Config {config_path} must be a mapping at the top level.")

    preset_name = raw.get("preset", "academic")
    preset_defaults = presets.load_preset_defaults(preset_name)
    merged = deep_merge(preset_defaults, raw)

    if env:
        environments = merged.get("environments", {})
        if env not in environments:
            raise ConfigError(
                f"Environment '{env}' is not defined under 'environments' in {config_path}."
            )
        merged = deep_merge(merged, environments[env])

    features = _load_features(site_dir, merged)
    merged["features"] = features
    site_meta = merged.get("site", {})
    theme = merged.get("theme", {"default": "system", "accent": "blue"})

    all_collection_data = merged.get("collections", {})
    disabled_collections = {
        key for key, data in all_collection_data.items() if not _enabled(data, key, features)
    }
    collections = {
        key: CollectionConfig.from_dict(key, data)
        for key, data in all_collection_data.items()
        if key not in disabled_collections
    }
    pages = [
        PageConfig.from_dict(p)
        for p in merged.get("pages", [])
        if _enabled(p, _page_feature_key(p), features, scope="pages")
        and not any(key in disabled_collections for key in p.get("collections", []))
    ]
    homepage = copy.deepcopy(merged.get("homepage", {}))
    homepage["sections"] = [
        section
        for section in homepage.get("sections", [])
        if _homepage_section_enabled(section, features, disabled_collections)
    ]
    nav = _resolve_nav(merged, pages, features)

    return Site(
        root=site_dir,
        data=merged,
        preset_name=preset_name,
        site=site_meta,
        theme=theme,
        collections=collections,
        pages=pages,
        homepage=homepage,
        nav=nav,
    )


def _resolve_nav(merged: dict, pages: list[PageConfig], features: dict[str, Any]) -> list[dict]:
    """Return an explicit nav if configured, else derive one from pages."""
    if "nav" in merged and merged["nav"]:
        return [
            dict(item)
            for item in merged["nav"]
            if _enabled(
                item,
                item.get("feature", item.get("slug", item.get("label", "nav"))),
                features,
                scope="navigation",
            )
        ]
    nav = [{"label": "Home", "slug": "", "href": None}]
    for page in pages:
        if page.nav:
            nav.append({"label": page.title, "slug": page.slug, "href": None})
    return nav
