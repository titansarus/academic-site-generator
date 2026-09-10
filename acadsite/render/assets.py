"""Static asset copying with a precedence chain.

Copy order (later overrides earlier when relative paths match):
1. core static defaults      (acadsite/static/core)
2. preset static defaults    (acadsite/presets/<name>/static)
3. site ``static/``
4. site ``assets/``

Everything lands under ``<output>/assets/`` so templates can reference a single
predictable prefix.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .. import presets
from ..paths import SitePathError, resolve_within


class UnsafeAssetError(ValueError):
    """Raised when an asset source or destination escapes its owning tree."""


def _copy_tree(src: Path, dest: Path, warnings: list[str], verbose: bool) -> None:
    for path in sorted(src.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(src)
        try:
            safe_source = resolve_within(src, rel, "Static asset")
            target = resolve_within(dest, rel, "Generated asset")
        except SitePathError as exc:
            raise UnsafeAssetError(str(exc)) from exc
        if target.exists() and verbose:
            warnings.append(f"asset override: {rel} (from {src})")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(safe_source, target)


def copy_static_assets(
    site,
    output_root: Path,
    verbose: bool = False,
) -> list[str]:
    """Copy all static asset roots into ``<output>/assets`` in precedence order."""
    warnings: list[str] = []
    assets_out = output_root / "assets"
    assets_out.mkdir(parents=True, exist_ok=True)

    core_static = Path(str(__import__("acadsite").__path__[0])) / "static" / "core"
    preset_static = presets.preset_static_path(site.preset_name)

    sources: list[Path] = []
    if core_static.is_dir():
        sources.append(core_static)
    if preset_static and preset_static.is_dir():
        sources.append(preset_static)
    for directory_name in ("static", "assets"):
        raw_source = site.root / directory_name
        if not raw_source.exists() and not raw_source.is_symlink():
            continue
        try:
            site_source = resolve_within(
                site.root, directory_name, f"Site {directory_name} directory"
            )
        except SitePathError as exc:
            raise UnsafeAssetError(str(exc)) from exc
        if site_source.is_dir():
            sources.append(site_source)

    for src in sources:
        _copy_tree(src, assets_out, warnings, verbose)
    return warnings
