from acadsite.config import deep_merge, load_site


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
