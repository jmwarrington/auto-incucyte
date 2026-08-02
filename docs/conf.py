"""Sphinx configuration for the auto-incucyte documentation."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

project = "auto-incucyte"
author = "J. M. Warrington"
copyright = "2026, J. M. Warrington"
version = "0.4"
release = "0.4.1"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.mathjax",
]
autosectionlabel_prefix_document = True
autodoc_typehints = "description"

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_theme_options = {
    "collapse_navigation": False,
    "navigation_depth": 4,
    "prev_next_buttons_location": "bottom",
    "style_external_links": True,
}
html_context = {
    "display_github": True,
    "github_user": "jmwarrington",
    "github_repo": "auto-incucyte",
    "github_version": "main",
    "conf_py_path": "/docs/",
}
