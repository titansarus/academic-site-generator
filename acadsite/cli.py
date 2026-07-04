"""Command-line interface for acadsite.

Commands:
    acadsite validate --site <dir> [--env <name>]
    acadsite build    --site <dir> --output <dir> [--env <name>] [-v]
    acadsite new      --site <dir>          (scaffold a minimal site)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import ConfigError, load_site
from .render.engine import build_site
from .validation import validate_site


def _cmd_validate(args: argparse.Namespace) -> int:
    try:
        site = load_site(args.site, env=args.env, config_filename=args.config)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2
    report = validate_site(site)
    for warning in report.warnings:
        print(f"warning: {warning}")
    for error in report.errors:
        print(f"error: {error}", file=sys.stderr)
    if report.ok:
        print(
            f"OK: '{site.title}' validated "
            f"({len(site.collections)} collections, {len(site.pages)} pages, "
            f"{len(report.warnings)} warnings)."
        )
        return 0
    print(f"FAILED: {len(report.errors)} error(s), {len(report.warnings)} warning(s).", file=sys.stderr)
    return 1


def _cmd_build(args: argparse.Namespace) -> int:
    try:
        site = load_site(args.site, env=args.env, config_filename=args.config)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2

    report = validate_site(site)
    for error in report.errors:
        print(f"error: {error}", file=sys.stderr)
    if not report.ok and not args.force:
        print("Build aborted due to validation errors. Use --force to override.", file=sys.stderr)
        return 1
    if args.verbose:
        for warning in report.warnings:
            print(f"warning: {warning}")

    result = build_site(site, args.output, verbose=args.verbose)
    for warning in result.warnings:
        print(f"warning: {warning}")
    output = Path(args.output).resolve()
    print(f"Built {len(result.pages)} pages into {output}")
    if site.custom_domain:
        print(f"CNAME written for {site.custom_domain}")
    return 0


def _cmd_new(args: argparse.Namespace) -> int:
    from .scaffold import scaffold_site

    target = Path(args.site)
    try:
        scaffold_site(target)
    except FileExistsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Scaffolded a new site at {target.resolve()}")
    print(f"Next: acadsite build --site {target} --output public")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="acadsite", description="Academic static site generator.")
    parser.add_argument("--version", action="version", version=f"acadsite {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="Validate site config and content.")
    p_validate.add_argument("--site", required=True, help="Path to the site directory.")
    p_validate.add_argument("--env", default=None, help="Environment overlay name.")
    p_validate.add_argument("--config", default=None, help="Alternate config filename inside the site dir.")
    p_validate.set_defaults(func=_cmd_validate)

    p_build = sub.add_parser("build", help="Build the static site.")
    p_build.add_argument("--site", required=True, help="Path to the site directory.")
    p_build.add_argument("--output", default="public", help="Output directory.")
    p_build.add_argument("--env", default=None, help="Environment overlay name.")
    p_build.add_argument("--config", default=None, help="Alternate config filename inside the site dir.")
    p_build.add_argument("-v", "--verbose", action="store_true", help="Verbose output.")
    p_build.add_argument("--force", action="store_true", help="Build despite validation errors.")
    p_build.set_defaults(func=_cmd_build)

    p_new = sub.add_parser("new", help="Scaffold a minimal new site.")
    p_new.add_argument("--site", required=True, help="Directory to create.")
    p_new.set_defaults(func=_cmd_new)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
