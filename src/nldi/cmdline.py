#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

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
"""
Command Line Interface for NLDI

This module provides a command line interface for the NLDI API tool,
implemented with ``click``.

"""

import click

from . import LOGGER, __version__
from .config import generate_alignment
from .openapi import generate_openapi_document


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=__version__, prog_name="nldi")
def cli():
    """NLDI Command Line Interface."""
    pass


@cli.group()
def config():
    """Manage configuration."""
    LOGGER.debug("SubCommand: `config` - Configuration Management")


@config.command()
@click.pass_context
@click.argument("config_file", type=click.File(encoding="utf-8"))
def align_sources(ctx, config_file):
    """Align Crawler Source table - update the source table with the configuration file"""
    if generate_alignment(config_file):
        click.echo("Successfully aligned crawler source table")
    else:
        click.echo("Unsuccessfully aligned crawler source table")


@cli.group()
def openapi():
    """OpenAPI management"""
    pass


@openapi.command()
@click.pass_context
@click.argument("config_file", type=click.File(encoding="utf-8"))
@click.option(
    "--format",
    "-f",
    "format_",
    type=click.Choice(["json", "yaml"]),
    default="yaml",
    help="Output format [json|yaml]",
)
@click.option(
    "--output-file",
    "-of",
    type=click.File("w", encoding="utf-8"),
    help="Name of output file",
)
def generate(ctx, config_file, output_file, format_="yaml"):
    """Generate OpenAPI Document."""
    if config_file is None:
        raise click.ClickException("--config/-c required")

    content = generate_openapi_document(config_file, format_)

    if output_file is None:
        click.echo(content)
    else:
        click.echo(f"Generating {output_file.name}")
        output_file.write(content)
        click.echo("Done")
