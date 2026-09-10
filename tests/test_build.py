from acadsite.config import load_site
from acadsite.render.engine import UnsafeOutputError, build_site
from acadsite.render.urls import UnsafeUrlError, UrlBuilder


def test_full_build(tmp_path, example_site_dir):
    site = load_site(example_site_dir)
    out = tmp_path / "public"
    result = build_site(site, out)

    # Core outputs exist
    assert (out / "index.html").exists()
    assert (out / "404.html").exists()
    assert (out / "sitemap.xml").exists()
    assert (out / "feed.xml").exists()  # feed enabled in demo config
    assert (out / ".acadsite-output").exists()

    # Collection page and a detail page
    assert (out / "publications" / "index.html").exists()
    assert (out / "projects" / "index.html").exists()
    assert (out / "projects" / "schedsim" / "index.html").exists()
    assert (out / "blog" / "why-scheduling-is-hard" / "index.html").exists()

    # Static assets copied
    assert (out / "assets" / "css" / "academic.css").exists()
    assert (out / "assets" / "js" / "navigation.js").exists()
    assert (out / "assets" / "js" / "theme-toggle.js").exists()

    # Homepage content
    index = (out / "index.html").read_text(encoding="utf-8")
    assert "Jordan Rivera" in index
    assert "Selected Publications" in index
    assert "data-layout-toggle" not in index
    assert "home-profile" in index
    assert "home-rest" in index
    assert "theme-icon-sun" in index and "theme-icon-moon" in index
    header = index.split("</header>", 1)[0]
    assert "View CV" not in header
    navigation_js = (out / "assets" / "js" / "navigation.js").read_text(encoding="utf-8")
    academic_js = (out / "assets" / "js" / "academic.js").read_text(encoding="utf-8")
    academic_css = (out / "assets" / "css" / "academic.css").read_text(encoding="utf-8")
    assert "animatePanel" in academic_js
    assert "fetchPage" in navigation_js
    assert "main.innerHTML = nextMain.innerHTML" in navigation_js
    assert "Page request left this site" in navigation_js
    assert "Destination is not an acadsite page" in navigation_js
    assert "history.pushState" in navigation_js
    assert "window.location.assign(destination.href)" in navigation_js
    assert "page-content-in" in academic_css
    assert "data-transition-state" in academic_css
    assert "prefers-reduced-motion" in academic_css
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
    minimal_js = (out / "assets" / "js" / "minimal.js").read_text(encoding="utf-8")
    navigation_js = (out / "assets" / "js" / "navigation.js").read_text(encoding="utf-8")
    minimal_css = (out / "assets" / "css" / "minimal.css").read_text(encoding="utf-8")
    assert "animatePanel" in minimal_js
    assert "fetchPage" in navigation_js
    assert "page-content-in" in minimal_css
    assert "data-transition-state" in minimal_css
    assert "prefers-reduced-motion" in minimal_css


def test_organization_logos_can_be_hidden_without_removing_data(example_site_dir, tmp_path):
    """A visual feature flag hides logos while content keeps logo fields."""
    import json

    site = load_site(example_site_dir)
    site.data["features"]["organization_logos"] = False
    out = tmp_path / "public"
    build_site(site, out)
    experience = (out / "experience" / "index.html").read_text(encoding="utf-8")
    assert "exp-logo" not in experience
    raw_items = json.loads((site.root / site.collections["experience"].source).read_text(encoding="utf-8"))
    assert raw_items[0].get("logo_initials")


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


def test_homepage_resolves_hero_collection_and_preview_groups(example_site_dir):
    site = load_site(example_site_dir)
    engine = __import__("acadsite.render.engine", fromlist=["Engine"]).Engine(site)
    engine.load()
    hero = engine._resolve_section(
        {"type": "hero", "source": "content/profile.json", "collection": "experience", "collection_limit": 1}
    )
    assert len(hero["collection_items"]) == 1

    grouped = engine._resolve_section(
        {
            "type": "collection_preview",
            "collection": "experience",
            "preview_groups": [{"label": "Research", "filter": {"category": "Research"}, "limit": 1}],
        }
    )
    assert grouped["preview_groups"][0]["label"] == "Research"
    assert len(grouped["preview_groups"][0]["items"]) <= 1


def test_no_hardcoded_page_renderers():
    """Guardrail: the engine must not define per-topic render functions."""
    import inspect

    from acadsite.render import engine

    source = inspect.getsource(engine)
    for banned in ("render_experience_page", "render_projects_page", "render_personal_page"):
        assert f"def {banned}" not in source


def test_clean_build_refuses_site_root_and_unknown_nonempty_directory(tmp_path):
    import pytest

    site_dir = _write_min_site(tmp_path, preset="academic")
    site = load_site(site_dir)
    with pytest.raises(UnsafeOutputError, match="protected output path"):
        build_site(site, site_dir)
    assert (site_dir / "site.config.json").exists()

    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    sentinel = unrelated / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")
    with pytest.raises(UnsafeOutputError, match="not recognized"):
        build_site(site, unrelated)
    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_clean_build_can_replace_its_own_marked_output(tmp_path):
    site_dir = _write_min_site(tmp_path, preset="academic")
    site = load_site(site_dir)
    out = tmp_path / "public"
    build_site(site, out)
    stale = out / "stale.txt"
    stale.write_text("old", encoding="utf-8")
    build_site(site, out)
    assert not stale.exists()
    assert (out / ".acadsite-output").exists()


def test_route_traversal_cannot_write_outside_output(tmp_path):
    import pytest

    site_dir = _write_min_site(tmp_path, preset="academic")
    site = load_site(site_dir)
    site.pages[0].slug = "../../escaped"
    out = tmp_path / "public"
    with pytest.raises(UnsafeUrlError, match="traversal"):
        build_site(site, out)
    assert not (tmp_path / "escaped" / "index.html").exists()

    with pytest.raises(UnsafeUrlError, match="escapes"):
        UrlBuilder.output_path(out, "/../../escaped/")


def test_site_templates_run_in_jinja_sandbox(tmp_path):
    import pytest
    from jinja2.exceptions import SecurityError

    site_dir = _write_min_site(tmp_path, preset="academic")
    override = site_dir / "templates" / "layouts" / "homepage.html.j2"
    override.parent.mkdir(parents=True)
    override.write_text(
        "{{ cycler.__init__.__globals__.os.getcwd() }}", encoding="utf-8"
    )
    with pytest.raises(SecurityError):
        build_site(load_site(site_dir), tmp_path / "public")


def test_site_template_symlink_cannot_read_outside_site(tmp_path):
    import pytest
    from acadsite.render.engine import Engine

    site_dir = _write_min_site(tmp_path, preset="academic")
    outside = tmp_path / "secret-template.txt"
    outside.write_text("PRIVATE TEMPLATE CONTENT", encoding="utf-8")
    override = site_dir / "templates" / "layouts" / "homepage.html.j2"
    override.parent.mkdir(parents=True)
    try:
        override.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlinks are unavailable: {exc}")

    engine = Engine(load_site(site_dir))
    source, filename, _ = engine.env.loader.get_source(
        engine.env, "layouts/homepage.html.j2"
    )
    assert "PRIVATE TEMPLATE CONTENT" not in source
    assert filename != str(outside)


def test_site_asset_symlink_cannot_publish_outside_file(tmp_path):
    import pytest
    from acadsite.render.assets import UnsafeAssetError

    site_dir = _write_min_site(tmp_path, preset="academic")
    outside = tmp_path / "private.txt"
    outside.write_text("PRIVATE ASSET CONTENT", encoding="utf-8")
    link = site_dir / "assets" / "leak.txt"
    link.parent.mkdir(parents=True)
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlinks are unavailable: {exc}")

    with pytest.raises(UnsafeAssetError, match="escapes"):
        build_site(load_site(site_dir), tmp_path / "public")


def test_unsafe_content_urls_are_neutralized(tmp_path):
    from acadsite.render.engine import Engine

    site = load_site(_write_min_site(tmp_path, preset="academic"))
    engine = Engine(site)
    assert engine.media_url("javascript:alert(1)") == "#"
    assert engine.media_url("data:text/html,unsafe") == "#"
    assert engine.media_url("https://example.com") == "https://example.com"
