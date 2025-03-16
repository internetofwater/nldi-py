#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""Generic util functions used in the code"""

import json
import os
import pathlib
import re
from functools import singledispatch
from io import TextIOWrapper
from pathlib import Path
from typing import IO, Any, Union

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import __version__

THISDIR = Path(__file__).parent.resolve()
TEMPLATES = THISDIR / "templates"

def url_join(*parts: str) -> str:
    """
    Join a URL from a number of parts/fragments.

    Implemented because urllib.parse.urljoin strips subpaths from
    host urls if they are specified.

    Per https://github.com/geopython/pygeoapi/issues/695

    Note that this function ALWAYS removes a trailing / for the output, even if
    your last term in the parts list includes the trailing slash.

    :param parts: list of parts to join
    :returns: str of resulting URL
    """
    return "/".join([str(p).strip().strip("/") for p in parts]).rstrip("/")


def to_json(dict_: dict, pretty: bool = False) -> str:
    # NOTE: mostly deprecated....   prefer to use flask.jsonify for return responses.  This func
    # is still used in the jinja template renderer.
    """
    Serialize dict to json

    :param dict_: `dict` of JSON representation
    :param pretty: `bool` of whether to prettify JSON (default is `False`)

    :returns: JSON string representation
    """
    if pretty:
        indent = 4
    else:
        indent = None

    return json.dumps(dict_, indent=indent)

def stream_j2_template(template: Path, data: dict) -> str:
    """
    Stream Jinja2 template

    :param template: template (relative path)
    :param data: dict of data

    :returns: string of rendered template
    """
    template_paths = [TEMPLATES, "."]
    env = Environment(
        loader=FileSystemLoader(template_paths), extensions=["jinja2.ext.i18n"], autoescape=select_autoescape()
    )

    env.filters["to_json"] = to_json
    env.globals.update(to_json=to_json)

    template = env.get_template(template)

    rv = template.stream(data=data)
    rv.enable_buffering(16)

    return rv
