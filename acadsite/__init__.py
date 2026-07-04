"""acadsite: a reusable static site generator.

The core engine is domain-agnostic. It knows how to load config and
structured content, render Markdown and Jinja templates, resolve a
template/asset override chain, and emit a static site. Academic concepts
(publications, experience, projects, service, blog, personal sections) live
in the ``academic`` preset and in site configuration, never as hardcoded
engine behavior.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
