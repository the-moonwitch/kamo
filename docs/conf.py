"""render the shared Markdown guides with Sphinx."""

from importlib.metadata import version as _version

project = "kamo"
author = "samhain"
release = _version("kamo")
version = release

extensions = ["myst_parser", "sphinx_rtd_theme"]
source_suffix = {".md": "markdown"}
myst_heading_anchors = 2
nitpicky = True
html_theme = "sphinx_rtd_theme"
html_show_copyright = False
html_show_sourcelink = False
