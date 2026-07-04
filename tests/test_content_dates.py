from acadsite import dates
from acadsite.config import load_site
from acadsite.content import apply_filter, load_collection, slugify


def test_slugify():
    assert slugify("Hello, World!") == "hello-world"
    assert slugify("  Multiple   Spaces ") == "multiple-spaces"
    assert slugify("") == "item"


def test_format_date_precision():
    assert dates.format_date("2025") == "2025"
    assert dates.format_date("2025-08") == "Aug 2025"
    assert dates.format_date("2025-08-15") == "Aug 15, 2025"
    assert dates.format_date(None) == ""


def test_display_date_present():
    item = {"start_date": "2023-08", "current": True}
    assert dates.display_date(item) == "Aug 2023 – Present"


def test_display_date_override():
    item = {"display_date": "Summer 2024", "start_date": "2024-06"}
    assert dates.display_date(item) == "Summer 2024"


def test_collection_sort_and_group(example_site_dir):
    site = load_site(example_site_dir)
    exp = load_collection(site, site.collections["experience"])
    # grouped by category
    categories = [g["category"] for g in exp.groups]
    assert "Academic" in categories
    # publications sorted by year desc
    pubs = load_collection(site, site.collections["publications"])
    years = [it.get("year") for it in pubs.items]
    assert years == sorted(years, reverse=True)


def test_apply_filter(example_site_dir):
    site = load_site(example_site_dir)
    pubs = load_collection(site, site.collections["publications"])
    selected = apply_filter(pubs.items, {"selected": True})
    assert all(it.get("selected") for it in selected)
    assert len(selected) == 2


def test_body_markdown_rendered(example_site_dir):
    site = load_site(example_site_dir)
    projects = load_collection(site, site.collections["projects"])
    schedsim = next(it for it in projects.items if it["title"] == "SchedSim")
    assert "<h2" in schedsim["body_html"]
