# =================================================================
#
# Author: Benjamin Webb <bwebb@lincolninst.edu>
#
# Copyright (c) 2023 Benjamin Webb
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# =================================================================

"""Generic util functions used in the code"""

import json
import logging
from pathlib import Path
from typing import IO
import yaml

from jinja2 import Environment, FileSystemLoader, select_autoescape

from nldi import __version__

LOGGER = logging.getLogger(__name__)

TEMPLATES = Path(__file__).parent.resolve() / 'templates'


def yaml_load(fh: IO) -> dict:
    """
    serializes a YAML files into a pyyaml object

    :param fh: file handle

    :returns: `dict` representation of YAML
    """

    return yaml.load(fh, Loader=yaml.SafeLoader)


def to_json(dict_: dict, pretty: bool = False) -> str:
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


def sort_sources(dict_: list) -> dict:
    """
    helper function to sort sources list by a dict key

    :param dict_: ``list``

    :returns: filtered ``dict``
    """

    return sorted(dict_, key=lambda d: d['crawler_source_id'])
