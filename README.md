# acadsite — Academic Static Site Generator

A small, reusable Python static site generator. The core engine is
**domain-agnostic**: it knows about *config*, *collections*, *pages*,
*components*, *templates*, and *static assets*. Everything academic
(publications, experience, projects, service, blog, personal notes) lives in a
swappable **preset** and in per-site **configuration** — never hardcoded into
the engine.

## Why this design

There are no functions like `render_experience_page()`. Instead the engine
exposes generic renderers:

- `render_page(page_config)` — one route, driven by a `layout` template
- `render_collection(collection_config)` — a list of items in some shape
- `render_homepage()` — a list of configured homepage sections
- `render_detail_page(collection, item)` — per-item pages

A page's shape comes from its `layout` (a template name) and the collections or
sections it references. To add a "publications" page you write config and,
optionally, a template — you do not touch Python.

## Install

```bash
python -m pip install -e .
```

This installs the `acadsite` command. (On Windows the script may live in a
`Scripts` directory that is not on `PATH`; `python -m acadsite.cli ...` always
works as a fallback.)

## Usage

```bash
acadsite new      --site mysite                       # scaffold a starter site
acadsite validate --site examples/basic-site          # check config + content
acadsite build    --site examples/basic-site --output public
acadsite build    --site . --output public --env github-pages
acadsite build    --site . --config site.theme2.json --output public2   # alternate theme
```

Newly scaffolded sites include `features.yml`, with global, homepage-only, and
standalone-page switches ready to edit.

Use `--config <file>` to point at an alternate config in the same site
directory — handy for shipping the **same content in multiple themes** (e.g. a
second config that sets `"preset": "minimal"` and shares the `content/` files).

Generated themes include progressive partial navigation. Navbar clicks fetch a
complete destination page but replace only its `<main>` region, synchronize the
document title and active navigation state, and use browser history normally.
Direct requests remain ordinary static HTML, and failed fetches fall back to a
full navigation.

## Presets

- **`academic`** — professional cards, timelines, and publication lists with a
  blue accent; the default.
- **`minimal`** — a personal, single-column, essay-like theme (warm paper,
  serif display type, monospace meta) for a site that reads like a personal
  page rather than a resume template.

A preset ships its own `templates/` (it may override `base.html.j2`),
`static/` assets, and optional `schemas/`. Switch presets with the `preset`
key in config; the engine and content model are identical across presets.

Try the bundled demo:

```bash
acadsite validate --site examples/basic-site
acadsite build --site examples/basic-site --output public
# open public/index.html
```

## Architecture

```
Core generator  ->  Academic preset  ->  Site configuration
```

| Layer | Location | Responsibility |
|-------|----------|----------------|
| Core engine | `acadsite/` | config, content, markdown, dates, rendering, validation, assets |
| Academic preset | `acadsite/presets/academic/` | academic templates, components, schemas, CSS/JS |
| Site | your repo | `site.config.json`, `content/`, `markdown/`, `assets/`, optional `templates/` overrides |

### Package layout

```
acadsite/
  cli.py            # validate / build / new
  config.py         # load + deep-merge config, preset defaults, env overlays
  content.py        # generic collection loading, sort/group/filter, body md
  dates.py          # partial-date parsing and display
  markdown.py       # Markdown -> HTML (math left for client-side rendering)
  bibtex.py         # BibTeX passthrough / synthesis
  scaffold.py       # `acadsite new`
  render/
    engine.py       # generic build engine
    urls.py         # base-path-aware URL + output-path helpers
    assets.py       # static asset copy with precedence
  templates/core/   # base.html.j2 + generic components + fallback layouts
  presets/academic/ # academic templates, components, schemas, static assets
  validation/       # config + content validators
```

## Content model

A collection is a JSON or YAML list of items. Common optional fields:

```json
{
  "title": "Required",
  "slug": "optional-slug",
  "summary": "Markdown summary",
  "body": "markdown/path.md",
  "date": "2026-07-04",
  "start_date": "2026-08", "end_date": null, "current": true,
  "display_date": "Aug 2026 – Present",
  "tags": ["tag"], "category": "group",
  "links": [{ "label": "GitHub", "url": "https://..." }],
  "image": "assets/images/x.png", "logo": "assets/logos/x.svg",
  "draft": false, "featured": false, "order": 10
}
```

Dates accept `YYYY`, `YYYY-MM`, or `YYYY-MM-DD`. `display_date` overrides
formatting; `current: true` with no `end_date` renders `Present`; undated items
sort last unless `order` is set.

### Collection types (academic preset)

`publication-list`, `timeline` (supports `group_by`), `cards` / `grid`,
`blog`, `markdown-sections`. Each maps to a component; you can override the
component per collection with `item_component`, or override the template file.

### Homepage sections

Configured in `homepage.sections`:

- `hero` — profile card (photo, bio, research interests, links)
- `news` / `list` — a simple dated list
- `collection_preview` — a limited preview of a collection with an optional
  `mode: "expandable"` (compact list + "show more") and `link_to_full_page`
- `markdown` — inline or file-based Markdown

## Template & asset overrides

Templates resolve through a `ChoiceLoader` chain (first match wins):

1. `‹site›/templates/`
2. `acadsite/presets/‹preset›/templates/`
3. `acadsite/templates/core/`

So a site can override one component (e.g. `templates/components/project_card.html.j2`)
without copying the whole theme. Static assets copy in precedence order
(core → preset → site `static/` → site `assets/`) into `public/assets/`.

## Feature flags

A site can keep section content on disk while disabling all of its generated
surfaces with a shared YAML file:

```json
{ "features_file": "features.yml" }
```

```yaml
blog: false
projects: true
homepage:
  personal_sections: false
pages:
  personal_sections: true
```

A disabled collection is omitted from navigation, homepage collection
previews, list/detail pages, and feeds. Collections, pages, and homepage
sections also accept a local `enabled: false` or an explicit `feature` key.
Nested `homepage` and `pages` mappings control those surfaces independently;
top-level flags are global master switches.

Presentation features can use the same mapping without changing the collection
model. The academic preset recognizes `organization_logos: false` to suppress
organization and university logo output while leaving logo fields and assets
available for later use.

## GitHub Pages

Use an `environments.github-pages` overlay to switch `base_url` / `base_path`
for project-page hosting, then:

```bash
acadsite build --site . --output public --env github-pages
```

The build emits `index.html`, `404.html`, `sitemap.xml`, `feed.xml` (when a
feed is configured), and `CNAME` (only when `site.custom_domain` is set).

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

## License

MIT — see [LICENSE](LICENSE).
