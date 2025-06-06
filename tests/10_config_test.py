#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0-1.0
#
"""Test ability to read/parse YAML config file."""

import logging
import os

import pytest

from nldi.config import MasterConfig, default, load_yaml


# region: withOUT env
# NOTE: These tests will succeed, but issue lots of warnings about environment variables
# note being defined, although referenced in the YAML.  See further below for tests where
# environment is set.
@pytest.mark.order(10)
@pytest.mark.unittest
def test_read_yaml_path(yaml_config_file):
    """Standard usage: read a YAML file into a dict, if given a pathlib.Path object."""
    cfg = load_yaml(yaml_config_file)
    assert cfg["logging"]["level"] == "DEBUG"
    assert cfg["server"]["url"] is None  # << Because NLDI_URL is not in environment here.
    assert cfg["metadata"]["identification"]["title"].startswith("Network Linked")
    assert len(cfg["metadata"]["identification"]["keywords"]) == 4


@pytest.mark.order(10)
@pytest.mark.unittest
def test_read_yaml_io(yaml_config_file):
    """If we pass an IO stream or file handle..."""
    with yaml_config_file.open() as fh:
        cfg = load_yaml(fh)
    assert cfg["logging"]["level"] == "DEBUG"
    assert cfg["server"]["url"] is None  # << Because NLDI_URL is not in environment here.
    assert cfg["metadata"]["identification"]["title"].startswith("Network Linked")
    assert len(cfg["metadata"]["identification"]["keywords"]) == 4


@pytest.mark.order(10)
@pytest.mark.unittest
def test_read_yaml_strpath(yaml_config_file):
    """If we pass a filename as a string..."""
    cfg = load_yaml(str(yaml_config_file))
    assert cfg["logging"]["level"] == "DEBUG"
    assert cfg["server"]["url"] is None  # << Because NLDI_URL is not in environment here.
    assert cfg["metadata"]["identification"]["title"].startswith("Network Linked")
    assert len(cfg["metadata"]["identification"]["keywords"]) == 4


@pytest.mark.order(11)
@pytest.mark.unittest
def test_cfg_from_yaml_noenv(yaml_config_file):
    """Parses the config file without having set environment variables which that YAML references."""
    settings = MasterConfig.from_yaml(yaml_config_file)
    assert settings.metadata.title.startswith("Network Link")
    assert settings.metadata.provider["name"] == "United States Geological Survey"


# region: WITH env
@pytest.mark.order(12)
@pytest.mark.unittest
def test_cfg_from_yaml_with_env(yaml_config_file, localhost_env_info, monkeypatch):
    for k, v in localhost_env_info.items():
        monkeypatch.setenv(k, v)

    settings = MasterConfig.from_yaml(yaml_config_file)
    assert settings.metadata.title.startswith("Network Link")
    assert settings.metadata.provider["name"] == "United States Geological Survey"
    assert settings.server.url == "https://localhost/"
