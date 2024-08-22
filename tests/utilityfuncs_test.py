#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#
import os
import nldi.util as util
import pytest


@pytest.mark.order(20)
@pytest.mark.unittest
def test_read_yaml_file(config_yaml, env_update):
    """Standard usage: read a YAML file into a dict, if given a pathlib.Path object."""
    os.environ.update(env_update)
    cfg = util.load_yaml(config_yaml)
    sources = cfg["sources"]
    assert len(sources) == 3
    suffixes = [src["source_suffix"] for src in sources]
    assert "WQP" in suffixes
    assert "nwissite" in suffixes
    assert "huc12pp" in suffixes


@pytest.mark.order(20)
@pytest.mark.unittest
def test_read_yaml_io(config_yaml, env_update):
    """If we pass an IO stream or file handle..."""
    os.environ.update(env_update)
    with config_yaml.open() as fh:
        cfg = util.load_yaml(fh)
    sources = cfg["sources"]
    assert len(sources) == 3


@pytest.mark.order(20)
@pytest.mark.unittest
def test_read_yaml_strpath(config_yaml, env_update):
    """If we pass a filename as a string..."""
    os.environ.update(env_update)
    cfg = util.load_yaml(str(config_yaml))
    sources = cfg["sources"]
    assert len(sources) == 3
