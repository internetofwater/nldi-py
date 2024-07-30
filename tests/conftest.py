#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#
"""Configuration for running pytest"""

import pytest
from click.testing import CliRunner


@pytest.fixture
def runner():
    """Runner for cli-related tests."""
    return CliRunner()
