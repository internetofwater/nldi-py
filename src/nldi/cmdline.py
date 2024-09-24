#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#


"""
Command Line Interface for NLDI

This module provides a command line interface for the NLDI API tool,
implemented with ``click``.

"""

import click
from sqlalchemy.engine.url import URL as DB_URL

from . import LOGGER, __version__
from .config import Configuration
from .api.plugins import CrawlerSourcePlugin
# from .config import align_crawler_sources
# from .openapi import generate_openapi_document


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
@click.argument("config_file", type=click.Path())  #              TODO: click.File vs click.Path
def align_sources(ctx, config_file):  #                                           TODO: do we need to pass context?
    """Align Crawler Source table - update the source table with the configuration file"""
    LOGGER.debug("SubCommand: `align_sources` - Align Crawler Source Table")
    cfg = Configuration(config_file)
    try:
        db_info = cfg.get("server", {}).get("data", {})
    except KeyError:
        click.echo("Unable to load configuration data.")
        return
    db_url = DB_URL.create(
            "postgresql+psycopg2",  # Default SQL dialect/driver
            username=db_info.get("user", "nldi"),
            password=db_info.get("password", "changeMe"),
            host=db_info.get("host", "localhost"),
            port=db_info.get("port", 5432),
            database=db_info.get("dbname", "nldi"),
        )
    src_plugin = CrawlerSourcePlugin("AlignCrawlerSources", db_connect_url=db_url)
    sources = cfg.get("sources", [])
    LOGGER.info(f"Will align {len(sources)} sources: {[f['source_suffix'] for f in sources]}")

    if src_plugin.align_sources(sources):
        click.echo("Successfully aligned crawler source table")
    else:
        click.echo("Unsuccessfully aligned crawler source table")


# @cli.group()
# def openapi():
#     """OpenAPI management"""
#     pass


# @openapi.command()
# @click.pass_context
# @click.argument("config_file", type=click.File(encoding="utf-8"))
# @click.option(
#     "--format",
#     "-f",
#     "format_",
#     type=click.Choice(["json", "yaml"]),
#     default="yaml",
#     help="Output format [json|yaml]",
# )
# @click.option(
#     "--output-file",
#     "-of",
#     type=click.File("w", encoding="utf-8"),
#     help="Name of output file",
# )
# def generate(ctx, config_file, output_file, format_="yaml"):
#     """Generate OpenAPI Document."""
#     if config_file is None:
#         raise click.ClickException("--config/-c required")

#     content = generate_openapi_document(config_file, format_)

#     if output_file is None:
#         click.echo(content)
#     else:
#         click.echo(f"Generating {output_file.name}")
#         output_file.write(content)
#         click.echo("Done")
