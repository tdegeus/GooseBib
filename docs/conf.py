import os
import sys

sys.path.insert(0, os.path.abspath(".."))

# Project information

project = "GooseBib"
copyright = "2017-2022, Tom de Geus"
author = "Tom de Geus"

# General configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.todo",
    "sphinxarg.ext",
    "sphinx.ext.autosectionlabel",
]

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Options for HTML output

html_theme = "sphinx_rtd_theme"
