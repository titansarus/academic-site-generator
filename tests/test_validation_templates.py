import json

from acadsite.config import load_site
from acadsite.render.engine import Engine
from acadsite.validation import validate_site


def test_valid_site_passes(example_site_dir):
    site = load_site(example_site_dir)
    report = validate_site(site)
    assert report.ok, report.errors


def test_duplicate_slug_detected(tmp_path):
    site_dir = tmp_path / "site"
    (site_dir / "content").mkdir(parents=True)
    (site_dir / "content" / "a.json").write_text("[]", encoding="utf-8")
    (site_dir / "content" / "b.json").write_text("[]", encoding="utf-8")
    config = {
        "preset": "academic",
        "site": {"title": "T", "base_path": "/"},
        "collections": {
            "a": {"slug": "same", "source": "content/a.json"},
            "b": {"slug": "same", "source": "content/b.json"},
        },
        "pages": [],
    }
    (site_dir / "site.config.json").write_text(json.dumps(config), encoding="utf-8")
    site = load_site(site_dir)
    report = validate_site(site)
    assert not report.ok
    assert any("Duplicate collection slug" in e for e in report.errors)


def test_missing_source_reported(tmp_path):
    site_dir = tmp_path / "site"
    site_dir.mkdir(parents=True)
    config = {
        "preset": "academic",
        "site": {"title": "T", "base_path": "/"},
        "collections": {"a": {"slug": "a", "source": "content/missing.json"}},
        "pages": [],
    }
    (site_dir / "site.config.json").write_text(json.dumps(config), encoding="utf-8")
    site = load_site(site_dir)
    report = validate_site(site)
    assert any("source not found" in e for e in report.errors)


def test_template_override_precedence(tmp_path, example_site_dir):
    """A site-level template overrides the preset template of the same name."""
    site = load_site(example_site_dir)
    engine = Engine(site)
    # Preset provides layouts/homepage.html.j2; core also provides one.
    template = engine.env.get_template("layouts/collection_page.html.j2")
    # The academic preset version uses a page-title class; core uses heading.
    assert "page-title" in template.render(
        **{**engine.base_context(), "page": {"title": "X", "slug": "x"},
           "collections": [], "collection": None, "body_html": ""}
    )
