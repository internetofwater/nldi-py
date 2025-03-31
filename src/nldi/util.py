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


def render_j2_template(template, data):
    global TEMPLATES
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=True)

    env.filters["to_json"] = to_json
    env.globals.update(to_json=to_json)

    env.filters["get_path_basename"] = get_path_basename
    env.globals.update(get_path_basename=get_path_basename)

    env.filters["get_breadcrumbs"] = get_breadcrumbs
    env.globals.update(get_breadcrumbs=get_breadcrumbs)

    env.filters["filter_dict_by_key_value"] = filter_dict_by_key_value
    env.globals.update(filter_dict_by_key_value=filter_dict_by_key_value)

    template = env.get_template(template)
    return template.render(data=data, version=__version__)


def to_json(dict_, pretty=False):
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

    return json.dumps(dict_, default=json_serial, indent=indent)


def get_path_basename(urlpath):
    """
    Helper function to derive file basename

    :param urlpath: URL path
    :returns: string of basename of URL path
    """
    return os.path.basename(urlpath)


def get_breadcrumbs(urlpath):
    """
    helper function to make breadcrumbs from a URL path

    :param urlpath: URL path
    :returns: `list` of `dict` objects of labels and links
    """
    links = []

    tokens = urlpath.split("/")

    s = ""
    for t in tokens:
        if s:
            s += "/" + t
        else:
            s = t
        links.append(
            {
                "href": s,
                "title": t,
            }
        )

    return links


def filter_dict_by_key_value(dict_, key, value):
    """
    helper function to filter a dict by a dict key

    :param dict_: ``dict``
    :param key: dict key
    :param value: dict key value

    :returns: filtered ``dict``
    """
    return {k: v for (k, v) in dict_.items() if v[key] == value}


def json_serial(obj):
    """
    Helper function to convert to JSON non-defaulttypes.

    Adapted from https://stackoverflow.com/a/22238613

    :param obj: `object` to be evaluated
    :returns: JSON non-default type to `str`
    """
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    elif isinstance(obj, bytes):
        try:
            return obj.decode("utf-8")
        except UnicodeDecodeError:
            return base64.b64encode(obj)
    elif isinstance(obj, Decimal):
        return float(obj)

    msg = "{} type {} not serializable".format(obj, type(obj))
    LOGGER.error(msg)
    raise TypeError(msg)
