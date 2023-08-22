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

from copy import deepcopy
import click
import io
import logging
from pathlib import Path
from typing import Union

from pygeoapi.util import get_base_url

from nldi.lookup.base import ProviderQueryError
from nldi.lookup.source import CrawlerSourceLookup
from nldi.util import yaml_load

LOGGER = logging.getLogger(__name__)


def generate_alignment(cfg_file: Union[Path, io.TextIOWrapper]):
    """
    Align Crawler Source from the configuration file

    :param cfg_file: configuration Path instance

    :returns: content of the OpenAPI document in the output
              format requested
    """
    if isinstance(cfg_file, Path):
        with cfg_file.open(mode='r') as cf:
            config = yaml_load(cf)
    else:
        config = yaml_load(cfg_file)

    if not config.get('sources'):
        LOGGER.debug('No sources to align with, continuing')
        return True

    provider_def = {
        'database': deepcopy(config['server']['data']),
        'base_url': get_base_url(config)
    }
    LOGGER.debug('Aligning configuration with crawler source table')
    try:
        crawler_source = CrawlerSourceLookup(provider_def)
        crawler_source.align_sources(config['sources'])
    except ProviderQueryError:
        LOGGER.error('Insufficient permission to update Crawler source')
        return False

    return True


@click.group()
def config():
    """Configuration management"""
    pass


@click.command()
@click.pass_context
@click.argument('config_file', type=click.File(encoding='utf-8'))
def align_sources(ctx, config_file):
    if generate_alignment(config_file):
        click.echo('Successfully aligned crawler source table')
    else:
        click.echo('Unsuccessfully aligned crawler source table')


config.add_command(align_sources)
