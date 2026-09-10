import pytest

from acadsite.config import ConfigError, deep_merge, load_site


def test_deep_merge_nested():
    base = {"a": {"x": 1, "y": 2}, "b": 3}
    overlay = {"a": {"y": 20, "z": 30}, "c": 4}
    result = deep_merge(base, overlay)
    assert result == {"a": {"x": 1, "y": 20, "z": 30}, "b": 3, "c": 4}
    # base is not mutated
    assert base["a"] == {"x": 1, "y": 2}


def test_load_site_basic(example_site_dir):
    site = load_site(example_site_dir)
    assert site.title == "Jordan Rivera"
    assert site.preset_name == "academic"
    assert "publications" in site.collections
    assert site.base_path == "/"
    # preset default merged in
    assert site.site.get("lang") == "en"


def test_env_overlay(example_site_dir):
    site = load_site(example_site_dir, env="github-pages")
    assert site.base_path == "/demo-site/"
    assert site.base_url == "https://example.github.io"
    assert site.custom_domain is None


def test_base_path_normalization(example_site_dir):
    site = load_site(example_site_dir, env="github-pages")
    assert site.base_path.startswith("/") and site.base_path.endswith("/")


def test_feature_file_disables_collection_everywhere(tmp_path):
    import json

    site_dir = tmp_path / "site"
    (site_dir / "content").mkdir(parents=True)
    (site_dir / "content" / "blog.json").write_text(
        json.dumps([{"title": "Hidden post"}]), encoding="utf-8"
    )
    (site_dir / "features.yml").write_text("blog: false\n", encoding="utf-8")
    (site_dir / "site.config.json").write_text(
        json.dumps({
            "preset": "academic",
            "site": {"title": "Feature test"},
            "features_file": "features.yml",
            "feed": {"enabled": True, "collection": "blog"},
            "collections": {"blog": {"source": "content/blog.json"}},
            "homepage": {"sections": [{"type": "collection_preview", "collection": "blog"}]},
            "pages": [{"title": "Blog", "slug": "blog", "collections": ["blog"]}],
        }),
        encoding="utf-8",
    )

    site = load_site(site_dir)
    assert "blog" not in site.collections
    assert site.pages == []
    assert site.homepage["sections"] == []
    assert all(item["label"] != "Blog" for item in site.nav)

    from acadsite.render.engine import build_site

    output = tmp_path / "public"
    build_site(site, output)
    assert not (output / "blog").exists()
    assert not (output / "feed.xml").exists()


def test_scoped_features_control_homepage_and_pages_independently(tmp_path):
    import json

    site_dir = tmp_path / "site"
    (site_dir / "content").mkdir(parents=True)
    for key in ("blog", "personal_sections"):
        (site_dir / "content" / f"{key}.json").write_text(
            json.dumps([{"title": key}]), encoding="utf-8"
        )
    (site_dir / "features.yml").write_text(
        "blog: true\n"
        "personal_sections: true\n"
        "homepage:\n"
        "  blog: false\n"
        "  personal_sections: true\n"
        "pages:\n"
        "  blog: true\n"
        "  personal_sections: false\n",
        encoding="utf-8",
    )
    collections = {
        key: {"source": f"content/{key}.json"}
        for key in ("blog", "personal_sections")
    }
    sections = [
        {"type": "collection_preview", "collection": key}
        for key in collections
    ]
    pages = [
        {"title": key, "slug": key, "collections": [key]}
        for key in collections
    ]
    (site_dir / "site.config.json").write_text(
        json.dumps({
            "preset": "academic",
            "site": {"title": "Scoped features"},
            "features_file": "features.yml",
            "collections": collections,
            "homepage": {"sections": sections},
            "pages": pages,
        }),
        encoding="utf-8",
    )

    site = load_site(site_dir)
    assert set(site.collections) == {"blog", "personal_sections"}
    assert [section["collection"] for section in site.homepage["sections"]] == [
        "personal_sections"
    ]
    assert [page.slug for page in site.pages] == ["blog"]
    assert [item["label"] for item in site.nav] == ["Home", "blog"]


def test_config_filename_and_features_cannot_escape_site_root(tmp_path):
    import json

    site_dir = tmp_path / "site"
    site_dir.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps({"preset": "academic"}), encoding="utf-8")
    with pytest.raises(ConfigError, match="escapes the site directory"):
        load_site(site_dir, config_filename="../outside.json")

    (site_dir / "site.config.json").write_text(
        json.dumps({"preset": "academic", "features_file": "../features.yml"}),
        encoding="utf-8",
    )
    (tmp_path / "features.yml").write_text("notes: true\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="escapes the site directory"):
        load_site(site_dir)


def test_autodetected_config_symlink_cannot_escape_site_root(tmp_path):
    import json

    site_dir = tmp_path / "site"
    site_dir.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps({"preset": "academic"}), encoding="utf-8")
    try:
        (site_dir / "site.config.json").symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlinks are unavailable: {exc}")
    with pytest.raises(ConfigError, match="escapes the site directory"):
        load_site(site_dir)
