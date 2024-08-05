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
import os
import pathlib
import re
from functools import singledispatch
from io import TextIOWrapper
from pathlib import Path
from typing import IO, Any, Union

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import LOGGER

THISDIR = Path(__file__).parent.resolve()
TEMPLATES = THISDIR / "templates"
SCHEMAS = THISDIR / "schemas"


def url_join(*parts: str) -> str:
    """
    Join a URL from a number of parts/fragments.

    Implemented because urllib.parse.urljoin strips subpaths from
    host urls if they are specified.

    Per https://github.com/geopython/pygeoapi/issues/695

    :param parts: list of parts to join
    :returns: str of resulting URL
    """
    return "/".join([str(p).strip().strip("/") for p in parts]).rstrip("/")


def yaml_load(fh: IO) -> dict:
    """
    Serialize a YAML file into a pyyaml object.

    :param fh: file handle
    :returns: `dict` representation of YAML
    """
    # support environment variables in config
    # https://stackoverflow.com/a/55301129
    path_matcher = re.compile(r".*\$\{([^}^{]+)\}.*")

    def path_constructor(loader, node):
        env_var = path_matcher.match(node.value).group(1)
        if env_var not in os.environ:
            raise EnvironmentError(f"Undefined environment variable {env_var} in config file.")
        return get_typed_value(os.path.expandvars(node.value))

    class EnvVarLoader(yaml.SafeLoader):
        pass

    EnvVarLoader.add_implicit_resolver("!path", path_matcher, None)
    EnvVarLoader.add_constructor("!path", path_constructor)

    try:
        _cfg = yaml.load(fh, Loader=EnvVarLoader)  # noqa: S506
    except EnvironmentError as err:
        LOGGER.error(err)
        return {}
    return _cfg


def get_typed_value(value: str) -> Union[float, int, str]:
    """
    Derive true type from data value

    :param value: value

    :returns: value as a native Python data type
    """
    try:
        if "." in value:  # float?
            value2 = float(value)
        elif len(value) > 1 and value.startswith("0"):
            value2 = value
        else:  # int?
            value2 = int(value)
    except ValueError:  # string (default)?
        value2 = value

    return value2


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


def stream_j2_template(template: Path, data: dict) -> str:
    """
    stream Jinja2 template

    :param template: template (relative path)
    :param data: dict of data

    :returns: string of rendered template
    """
    template_paths = [TEMPLATES, "."]

    LOGGER.debug(f"using templates: {TEMPLATES}")

    env = Environment(
        loader=FileSystemLoader(template_paths), extensions=["jinja2.ext.i18n"], autoescape=select_autoescape()
    )

    env.filters["to_json"] = to_json
    env.globals.update(to_json=to_json)

    template = env.get_template(template)

    rv = template.stream(data=data)
    rv.enable_buffering(16)

    return rv


def sort_sources(dict_: list) -> dict:
    """help sort sources list by a dict key."""
    return sorted(dict_, key=lambda d: d["crawler_source_id"])


# region refactors
@singledispatch
def load_yaml(fromwhere: Any) -> dict:
    """
    Load a YAML file or stream into a Python dict.

    This is a generic function that can handle arguments of various types.
    See the other implementations for specific types.

    * str - will convert to a Path and call the Path implementation
    * pathlib.Path - will open the Path and pass the file handle to the TextIOWrapper implementation
    * TextIOWrapper - will read the stream and attempt to parse it
    """
    raise NotImplementedError(f"Unsupported type: {type(fromwhere)}")


@load_yaml.register
def _(fromwhere: TextIOWrapper) -> dict:
    # support environment variables in config
    # https://stackoverflow.com/a/55301129
    path_matcher = re.compile(r".*\$\{([^}^{]+)\}.*")

    def path_constructor(loader, node):
        env_var = path_matcher.match(node.value).group(1)
        if env_var not in os.environ:
            raise EnvironmentError(f"Undefined environment variable {env_var} in config file.")
        return get_typed_value(os.path.expandvars(node.value))

    class EnvVarLoader(yaml.SafeLoader):
        pass

    EnvVarLoader.add_implicit_resolver("!path", path_matcher, None)
    EnvVarLoader.add_constructor("!path", path_constructor)

    try:
        _cfg = yaml.load(fromwhere, Loader=EnvVarLoader)  # noqa: S506
    except EnvironmentError as err:
        LOGGER.error(err)
        return {}
    return _cfg


@load_yaml.register(pathlib.Path)
def _(fromwhere: pathlib.Path) -> dict:
    if not fromwhere.exists():
        raise FileNotFoundError(f"File not found: {fromwhere}")
    with fromwhere.open() as fh:
        return load_yaml(fh)


@load_yaml.register(str)
def _(fromwhere: str) -> dict:
    return load_yaml(pathlib.Path(fromwhere))
