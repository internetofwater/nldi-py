#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

"""
CLI interface testing

Tests "routing" to ensure that subcommands and switches are working as expected.
"""

import pytest
from nldi.cmdline import cli as nldi_cmd


@pytest.mark.order(5)
@pytest.mark.unittest
def test_cli(runner):
    """Test CLI can be invoked in test context."""
    result = runner.invoke(nldi_cmd, ["--version"])
    assert result.exit_code == 0
    # NOTE: we are not testing any output or if the business logic is working correctly.
    # This just tests that we can call the CLI with this switch and it doesn't produce an error.


@pytest.mark.order(5)
@pytest.mark.unittest
def test_subcommands(runner):
    """
    Subcommands we expect are present.

    >>> nldi
        Should produce help message; a subcommand is required.

    >>> nldi no_such_subcommand
        Should produce help messages and a non-zero exit code.
    """
    result = runner.invoke(nldi_cmd)  # with no subcommand
    assert result.exit_code == 0
    assert result.output.startswith("Usage:")  ## should get the help message

    result = runner.invoke(nldi_cmd, ["nonesuch"])
    assert result.exit_code != 0
    assert "Error: No such command" in result.output

    # result = runner.invoke(nldi_cmd, ["config", "align-sources", "./tests/data/sources_config.yml"])
    # assert result.exit_code == 0
    # assert "Undefined environment variable NLDI_URL in config file" in result.output
