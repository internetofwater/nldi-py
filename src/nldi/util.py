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

from . import LOGGER, __version__

THISDIR = Path(__file__).parent.resolve()
TEMPLATES = THISDIR / "templates"
SCHEMAS = THISDIR / "schemas"


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


def yaml_load(fh: IO) -> dict:
    # NOTE: deprecated in favor of refactored version below
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
    """Help sort sources list by a dict key."""
    return sorted(dict_, key=lambda d: d["crawler_source_id"])


# region Refactored Functions
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
    LOGGER.debug(f"Reading YAML from... {fromwhere.__class__.__name__}")
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
    """
    Load a YAML file into a Python dict.

    This implementation opens the file and passes the file handle to the
    TextIOWrapper implementation, which is where the real work happens.
    """
    LOGGER.debug(f"Reading YAML: {fromwhere.__repr__()}")
    if not fromwhere.exists():
        raise FileNotFoundError(f"File not found: {fromwhere}")
    with fromwhere.open() as fh:
        return load_yaml(fh)


@load_yaml.register(str)
def _(fromwhere: str) -> dict:
    """
    Load a YAML file into a Python dict.

    This is a convenience function that converts the string argument to a
    Path and calls the Path implementation.
    """
    LOGGER.debug(f"Reading YAML: {fromwhere.__repr__()}")
    return load_yaml(pathlib.Path(fromwhere))


@load_yaml.register(dict)
def _(fromwhere: dict) -> dict:
    """Already a dictionary... nothing to do here."""
    # assumes that the necessary keys are present
    return fromwhere


# region Borrowed from PyGeoAPI

# The following functions were borrowed from the PyGeoAPI project, which is licensed under the MIT License.
# The PyGeoAPI license is here: https://docs.pygeoapi.io/en/0.9.0/license.html, and reproduced below:
#
# The MIT License (MIT)
# Copyright &copy; 2018-2020 Tom Kralidis
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
# associated documentation files (the “Software”), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the
# following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
# LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN
# NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR
# THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# See https://docs.pygeoapi.io/en/0.9.0/_modules/pygeoapi/util.html for the original source code.


#    We include these utils here to remove the dependency on the entire pygeoapi package..
#    We are just using a couple of helpler utilities to render templates for openapi, so don't need
#    the whole thing.


def render_j2_template(config, template, data):
    """
    render Jinja2 template

    :param config: dict of configuration
    :param template: template (relative path)
    :param data: dict of data

    :returns: string of rendered template
    """
    try:
        templates_path = config["server"]["templates"]["path"]
        env = Environment(loader=FileSystemLoader(templates_path), autoescape=True)
        LOGGER.debug("using custom templates: {}".format(templates_path))
    except (KeyError, TypeError):
        env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=True)
        LOGGER.debug("using default templates: {}".format(TEMPLATES))

    env.filters["to_json"] = to_json
    env.globals.update(to_json=to_json)

    env.filters["get_path_basename"] = get_path_basename
    env.globals.update(get_path_basename=get_path_basename)

    env.filters["get_breadcrumbs"] = get_breadcrumbs
    env.globals.update(get_breadcrumbs=get_breadcrumbs)

    env.filters["filter_dict_by_key_value"] = filter_dict_by_key_value
    env.globals.update(filter_dict_by_key_value=filter_dict_by_key_value)

    template = env.get_template(template)
    return template.render(config=config, data=data, version=__version__)


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
            LOGGER.debug("Returning as UTF-8 decoded bytes")
            return obj.decode("utf-8")
        except UnicodeDecodeError:
            LOGGER.debug("Returning as base64 encoded JSON object")
            return base64.b64encode(obj)
    elif isinstance(obj, Decimal):
        return float(obj)

    msg = "{} type {} not serializable".format(obj, type(obj))
    LOGGER.error(msg)
    raise TypeError(msg)
