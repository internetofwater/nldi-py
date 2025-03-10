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

from . import LOGGER, __version__


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
