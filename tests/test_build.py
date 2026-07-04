from acadsite.config import load_site
from acadsite.render.engine import build_site


def test_full_build(tmp_path, example_site_dir):
    site = load_site(example_site_dir)
    out = tmp_path / "public"
    result = build_site(site, out)

    # Core outputs exist
    assert (out / "index.html").exists()
    assert (out / "404.html").exists()
    assert (out / "sitemap.xml").exists()
    assert (out / "feed.xml").exists()  # feed enabled in demo config

    # Collection page and a detail page
    assert (out / "publications" / "index.html").exists()
    assert (out / "projects" / "index.html").exists()
    assert (out / "projects" / "schedsim" / "index.html").exists()
    assert (out / "blog" / "why-scheduling-is-hard" / "index.html").exists()

    # Static assets copied
    assert (out / "assets" / "css" / "academic.css").exists()
    assert (out / "assets" / "js" / "theme-toggle.js").exists()

    # Homepage content
    index = (out / "index.html").read_text(encoding="utf-8")
    assert "Jordan Rivera" in index
    assert "Selected Publications" in index
    assert result.pages


def test_github_pages_build(tmp_path, example_site_dir):
    site = load_site(example_site_dir, env="github-pages")
    out = tmp_path / "public"
    build_site(site, out)
    index = (out / "index.html").read_text(encoding="utf-8")
    # base_path applied to internal links
    assert "/demo-site/" in index
    # ...but the file tree is relative to base_path (no double prefix on Pages)
    assert (out / "projects" / "index.html").exists()
    assert not (out / "demo-site").exists()
    # sitemap uses absolute URLs including the base_path
    sitemap = (out / "sitemap.xml").read_text(encoding="utf-8")
    assert "https://example.github.io/demo-site/" in sitemap
    # custom_domain disabled -> no CNAME
    assert not (out / "CNAME").exists()


def test_cname_written_when_custom_domain(tmp_path):
    import json

    site_dir = tmp_path / "site"
    (site_dir / "content").mkdir(parents=True)
    (site_dir / "content" / "n.json").write_text(
        json.dumps([{"title": "Hi"}]), encoding="utf-8"
    )
    config = {
        "preset": "academic",
        "site": {"title": "T", "base_path": "/", "custom_domain": "example.org"},
        "collections": {"n": {"slug": "n", "source": "content/n.json"}},
        "homepage": {"sections": []},
        "pages": [{"title": "N", "slug": "n", "layout": "collection_page", "collections": ["n"]}],
    }
    (site_dir / "site.config.json").write_text(json.dumps(config), encoding="utf-8")
    from acadsite.config import load_site

    site = load_site(site_dir)
    out = tmp_path / "public"
    build_site(site, out)
    assert (out / "CNAME").read_text(encoding="utf-8").strip() == "example.org"


def test_no_hardcoded_page_renderers():
    """Guardrail: the engine must not define per-topic render functions."""
    import inspect

    from acadsite.render import engine

    source = inspect.getsource(engine)
    for banned in ("render_experience_page", "render_projects_page", "render_personal_page"):
        assert f"def {banned}" not in source
