from acadsite.config import load_site
from acadsite.render.engine import build_site
from acadsite.scaffold import scaffold_site


def test_scaffold_includes_scoped_feature_layout(tmp_path):
    site_dir = tmp_path / "new-site"
    scaffold_site(site_dir)

    feature_file = site_dir / "features.yml"
    assert feature_file.exists()
    text = feature_file.read_text(encoding="utf-8")
    assert "homepage:" in text
    assert "pages:" in text

    site = load_site(site_dir)
    assert "notes" in site.collections
    assert [section.get("collection") for section in site.homepage["sections"]][-1] == "notes"
    assert [page.slug for page in site.pages] == ["notes"]

    output = tmp_path / "public"
    build_site(site, output)
    assert (output / "index.html").exists()
    assert (output / "notes" / "index.html").exists()
