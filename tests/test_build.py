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


def _write_min_site(tmp_path, preset, config_name="site.config.json"):
    import json

    site_dir = tmp_path / "site"
    (site_dir / "content").mkdir(parents=True, exist_ok=True)
    (site_dir / "content" / "profile.json").write_text(
        json.dumps({"name": "Ada L.", "tagline": "engineer", "about": "Hello."}),
        encoding="utf-8",
    )
    (site_dir / "content" / "pubs.json").write_text(
        json.dumps([{"title": "A Paper", "authors": "Ada L.", "year": 2025}]),
        encoding="utf-8",
    )
    config = {
        "preset": preset,
        "site": {"title": "Ada L.", "base_path": "/"},
        "collections": {"publications": {"slug": "publications", "source": "content/pubs.json", "type": "publication-list"}},
        "homepage": {"sections": [
            {"type": "hero", "source": "content/profile.json"},
            {"type": "collection_preview", "collection": "publications", "limit": 3},
        ]},
        "pages": [{"title": "Publications", "slug": "publications", "layout": "collection_page", "collections": ["publications"]}],
    }
    (site_dir / config_name).write_text(json.dumps(config), encoding="utf-8")
    return site_dir


def test_minimal_preset_build(tmp_path):
    """The 'minimal' preset builds and produces its own distinct chrome."""
    from acadsite.config import load_site

    site_dir = _write_min_site(tmp_path, preset="minimal")
    out = tmp_path / "public"
    build_site(load_site(site_dir), out)
    index = (out / "index.html").read_text(encoding="utf-8")
    assert "Hi, I'm Ada L." in index
    # Uses the minimal stylesheet, not the academic one.
    assert (out / "assets" / "css" / "minimal.css").exists()
    assert not (out / "assets" / "css" / "academic.css").exists()
    assert "minimal.css" in index and "academic.css" not in index


def test_alternate_config_filename(tmp_path):
    """A second config file in the same site dir can select another theme."""
    from acadsite.config import load_site

    site_dir = _write_min_site(tmp_path, preset="academic")  # default site.config.json
    # Add a second config using the minimal preset.
    import json

    alt = dict(json.loads((site_dir / "site.config.json").read_text(encoding="utf-8")))
    alt["preset"] = "minimal"
    (site_dir / "site.theme2.json").write_text(json.dumps(alt), encoding="utf-8")

    default_site = load_site(site_dir)
    alt_site = load_site(site_dir, config_filename="site.theme2.json")
    assert default_site.preset_name == "academic"
    assert alt_site.preset_name == "minimal"


def test_academic_project_showcase_is_packaged(example_site_dir, tmp_path):
    """The comparison layout is preset-owned, not copied into a consuming site."""
    site = load_site(example_site_dir)
    projects_page = next(page for page in site.pages if page.slug == "projects")
    projects_page.layout = "projects_showcase"
    out = tmp_path / "public"
    build_site(site, out)
    html = (out / "projects" / "index.html").read_text(encoding="utf-8")
    assert "Design A" in html
    assert "Design B" in html


def test_no_hardcoded_page_renderers():
    """Guardrail: the engine must not define per-topic render functions."""
    import inspect

    from acadsite.render import engine

    source = inspect.getsource(engine)
    for banned in ("render_experience_page", "render_projects_page", "render_personal_page"):
        assert f"def {banned}" not in source
