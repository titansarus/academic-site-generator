"""Jinja loaders with filesystem-boundary enforcement."""

from __future__ import annotations

import os
from pathlib import Path

from jinja2 import FileSystemLoader, TemplateNotFound
from jinja2.loaders import split_template_path

from ..paths import SitePathError, resolve_within


class ContainedFileSystemLoader(FileSystemLoader):
    """Load overrides without following a template symlink outside its root."""

    def get_source(self, environment, template):
        pieces = split_template_path(template)
        for searchpath in self.searchpath:
            root = Path(searchpath).resolve()
            try:
                filename = resolve_within(
                    root, Path(*pieces), f"Template '{template}'"
                )
            except SitePathError:
                continue
            if not filename.is_file():
                continue

            contents = filename.read_text(encoding=self.encoding)
            mtime = filename.stat().st_mtime

            def uptodate(path=filename, expected=mtime):
                try:
                    return os.path.getmtime(path) == expected
                except OSError:
                    return False

            return contents, os.path.normpath(str(filename)), uptodate

        raise TemplateNotFound(
            template,
            f"{template!r} was not found in a contained template search path",
        )
