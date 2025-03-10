#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""YAML-related utilities."""

import logging
import os
import pathlib
import re
from functools import singledispatch
from io import TextIOWrapper
from pathlib import Path
from typing import IO, Any, Union

import yaml


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


@singledispatch
def load_yaml(fromwhere: Any) -> dict[str, Any]:
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
def _(fromwhere: TextIOWrapper) -> dict[str, Any]:
    logging.debug(f"Reading YAML from... {fromwhere.__class__.__name__}")
    # support environment variables in config  https://stackoverflow.com/a/55301129
    path_matcher = re.compile(r".*\$\{([^}^{]+)\}.*")

    def path_constructor(loader, node):
        env_var = path_matcher.match(node.value).group(1)
        if env_var not in os.environ:
            logging.warning(f"Undefined environment variable {env_var} in config file.")
            _value = None
        else:
            _value = get_typed_value(os.path.expandvars(node.value))
        return _value

    class EnvVarLoader(yaml.SafeLoader):
        pass

    EnvVarLoader.add_implicit_resolver("!path", path_matcher, None)
    EnvVarLoader.add_constructor("!path", path_constructor)

    try:
        _cfg = yaml.load(fromwhere, Loader=EnvVarLoader)  # noqa: S506
    except EnvironmentError as err:
        logging.error(err)
        return {}
    return _cfg


@load_yaml.register(pathlib.Path)
def _(fromwhere: pathlib.Path) -> dict[str, Any]:
    """
    Load a YAML file into a Python dict.

    This implementation opens the file and passes the file handle to the
    TextIOWrapper implementation, which is where the real work happens.
    """
    logging.debug(f"Reading YAML: {fromwhere.__repr__()}")
    if not fromwhere.exists():
        raise FileNotFoundError(f"File not found: {fromwhere}")
    with fromwhere.open() as fh:
        return load_yaml(fh)


@load_yaml.register(str)
def _(fromwhere: str) -> dict[str, Any]:
    """
    Load a YAML file into a Python dict.

    This is a convenience function that converts the string argument to a
    Path and calls the Path implementation.
    """
    logging.debug(f"Reading YAML: {fromwhere.__repr__()}")
    return load_yaml(pathlib.Path(fromwhere))


@load_yaml.register(dict)
def _(fromwhere: dict) -> dict[str, Any]:
    """Already a dictionary... nothing to do here."""
    # assumes that the necessary keys are present
    return fromwhere
