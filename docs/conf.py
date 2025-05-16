#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

"""Configuration for SPHINX document generator."""

project = "NLDI API Service (python)"
author = "Internet of Water"
copyright = f"2024, {author}"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
    "myst_parser",
    "sphinx_rtd_theme",
    "sphinxcontrib.mermaid",
    "sphinx.ext.intersphinx",
]
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
autodoc_default_options = {"member-order": "bysource"}
intersphinx_mapping = {"sqlalchemy": ("http://docs.sqlalchemy.org/en/stable/", None)}
