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
import io
import logging
from pathlib import Path
from typing import Union

import click
import yaml

from pygeoapi.models.openapi import OAPIFormat
from pygeoapi.util import get_base_url

from nldi import __version__
from nldi.util import THISDIR, sort_sources, url_join, yaml_load, to_json

LOGGER = logging.getLogger(__name__)

with open(THISDIR / 'openapi' / 'schemas.yaml', 'r') as fh:
    OAS_SCHEMAS = yaml_load(fh)

with open(THISDIR / 'openapi' / 'parameters.yaml', 'r') as fh:
    OAS_PARAMETERS = yaml_load(fh)

with open(THISDIR / 'openapi' / 'responses.yaml', 'r') as fh:
    OAS_RESPONSES = yaml_load(fh)

RESPONSES = {
    '400': {'$ref': '#/components/responses/400'},
    '404': {'$ref': '#/components/responses/404'},
    '406': {'$ref': '#/components/responses/406'},
    '500': {'$ref': '#/components/responses/500'}
}


def get_oas(cfg):
    """
    Generates an OpenAPI 3.0 Document

    :param cfg: pygeoapi-like configuration object

    :returns: OpenAPI definition YAML dict
    """

    cfg = deepcopy(cfg)

    LOGGER.debug('Generating OpenAPI document')
    oas = {
        'openapi': '3.0.1',
        'info': {},
        'servers': {},
        'components': {
            'schemas': OAS_SCHEMAS,
            'responses': OAS_RESPONSES,
            'parameters': OAS_PARAMETERS
        },
        'tags': []
    }

    oas['info'] = {
        'title': cfg['metadata']['identification']['title'],
        'description': cfg['metadata']['identification']['description'],
        'x-keywords': cfg['metadata']['identification']['keywords'],
        'termsOfService':
            cfg['metadata']['identification']['terms_of_service'],
        'contact': {
            'name': cfg['metadata']['provider']['name'],
            'url': cfg['metadata']['provider']['url'],
        },
        'license': {
            'name': cfg['metadata']['license']['name'],
            'url': cfg['metadata']['license']['url']
        },
        'version': __version__
    }

    oas['servers'] = [
        {
            'url': get_base_url(cfg),
            'description': cfg['metadata']['identification']['title']
        }, {
            'url': 'https://labs.waterdata.usgs.gov/api/nldi',
            'description': 'Network Linked Data Index API'
        }, {
            'url': 'https://labs-beta.waterdata.usgs.gov/api/nldi/',
            'description': 'Network Linked Data Index API - Beta'
        }
    ]

    paths = {}
    tags = [
        {
            'description': 'NLDI home',
            'externalDocs': {
                'description': 'information',
                'url': 'https://github.com/internetofwater/nldi-services'
            },
            'name': 'nldi'
        }, {
            'description': 'NHDPlus Version 2 COMID',
            'externalDocs': {
                'description': 'information',
                'url': 'https://www.usgs.gov/national-hydrography/national-hydrography-dataset'  # noqa
            },
            'name': 'comid'
        }
    ]

    paths['/'] = {
        'get': {
            'summary': 'getLandingPage',
            'description': 'Landing page',
            'tags': ['nldi'],
            'operationId': 'getLandingPage',
            'responses': {
                '200': {'description': 'OK'},
                '400': {'$ref': '#/components/responses/400'},
                '500': {'$ref': '#/components/responses/500'},
            }
        }
    }

    paths['/openapi'] = {
        'get': {
            'summary': 'getOpenAPI',
            'description': 'This document',
            'tags': ['nldi'],
            'operationId': 'getOpenAPI',
            'responses': {
                '200': {'description': 'OK'},
                '400': {'$ref': '#/components/responses/400'},
                '500': {'$ref': '#/components/responses/500'},
            }
        }
    }

    # paths['/lookups'] = {
    #     'get': {
    #         'summary': 'getLookups',
    #         'description': 'Returns characteristics types',
    #         'tags': ['nldi'],
    #         'operationId': 'getLookups',
    #         'responses': RESPONSES
    #     }
    # }

    # paths['/lookups/{characteristicType}/characteristics'] = {
    #     'get': {
    #         'summary': 'getLookupsCharacteristics',
    #         'description': 'Returns available characteristics metadata',
    #         'tags': ['nldi'],
    #         'operationId': 'getLookupsCharacteristics',
    #         'parameters': [
    #             {'$ref': '#/components/parameters/characteristicType'}
    #         ],
    #         'responses': RESPONSES
    #     }
    # }

    paths['/linked-data'] = {
        'get': {
            'summary': 'getDataSources',
            'description': 'Returns a list of data sources',
            'tags': ['nldi'],
            'operationId': 'getDataSources',
            'responses': {
                '200': {
                    'description': 'OK',
                    'content': {
                        'application/json': {
                            'schema': {
                                '$ref': '#/components/schemas/DataSourceList'
                            }
                        }
                    }
                },
                **RESPONSES
            }
        }
    }

    paths['/linked-data/hydrolocation'] = {
        'get': {
            'summary': 'getHydrologicLocation',
            'description': ('Returns the hydrologic location closest to '
                            'a provided set of coordinates.'),
            'tags': ['nldi'],
            'operationId': 'getHydrologicLocation',
            'parameters': [
                {'$ref': '#/components/parameters/coords'}
            ],
            'responses': {
                '200': {
                    'description': 'OK',
                    'content': {
                        'application/json': {
                            'schema': {
                                '$ref': '#/components/schemas/FeatureCollection'  # noqa
                            }
                        }
                    }
                },
                **RESPONSES
            }
        }
    }

    comid = {
        'source_suffix': 'comid',
        'source_name': 'NHDPlus comid'
    }
    sources = [comid, *sort_sources(cfg['sources'])]
    _sources = [_src['source_suffix'] for _src in cfg['sources']]
    for src in sources:
        src_id = src['source_suffix'].lower()
        src_name = src['source_name']
        src_path = f'/linked-data/{src_id}'
        src_title = f'get{src_id.title()}'
        LOGGER.debug(f'Processing {src_id}')

        if src_id != 'comid':
            paths[src_path] = {
                'get': {
                    'summary': src_title,
                    'description': src_name,
                    'tags': [src_id],
                    'operationId': src_title,
                    'responses': {
                        '200': {
                            'description': 'OK',
                            'content': {
                                'application/json': {
                                    'schema': {
                                        '$ref': '#/components/schemas/FeatureCollection'  # noqa
                                    }
                                },
                                'application/ld+json': {
                                    'schema': {
                                        '$ref': '#/components/schemas/FeatureCollection'  # noqa
                                    }
                                }
                            }
                        },
                        **RESPONSES
                    }
                }
            }
            tags.append({'description': src_name, 'name': src_id})

            id_field = '{identifier}'
            parameters = [
                {'$ref': '#/components/parameters/identifier'}
            ]

        else:
            src_by_pos = url_join('/', src_path, 'position')
            paths[src_by_pos] = {
                'get': {
                    'summary': f'{src_title}ByCoordinates',
                    'description': ('returns the feature closest to a '
                                    'provided set of coordinates'),
                    'tags': [src_id],
                    'operationId': f'{src_title}ByCoordinates',
                    'parameters': [
                        {'$ref': '#/components/parameters/coords'}
                    ],
                    'responses': {
                        '200': {
                            'description': 'OK',
                            'content': {
                                'application/json': {
                                    'schema': {
                                        '$ref': '#/components/schemas/Feature'
                                    }
                                }
                            }
                        },
                        **RESPONSES
                    }
                }
            }

            id_field = '{comid}'
            parameters = [{
                'name': 'comid',
                'in': 'path',
                'description': 'NHDPlus common identifier',
                'required': True,
                'schema': {
                    'type': 'integer',
                    'example': 13294314
                }
            }]

        src_by_feature = url_join('/', src_path, id_field)
        paths[src_by_feature] = {
            'get': {
                'summary': f'{src_title}ById',
                'description': ('returns registered feature as WGS84 lat/lon '
                                'GeoJSON if it exists'),
                'tags': [src_id],
                'operationId': f'{src_title}ById',
                'parameters': parameters,
                'responses': {
                    '200': {
                        'description': 'OK',
                        'content': {
                            'application/json': {
                                'schema': {
                                    '$ref': '#/components/schemas/FeatureCollection'  # noqa
                                }
                            },
                            'application/ld+json': {
                                'schema': {
                                    '$ref': '#/components/schemas/FeatureCollection'  # noqa
                                }
                            },
                            'application/vnd.geo+json': {
                                'schema': {
                                    '$ref': '#/components/schemas/FeatureCollection'  # noqa
                                }
                            }
                        }
                    },
                    **RESPONSES
                }
            }
        }

        # src_by_char = url_join('/', src_by_feature, '{characteristicType}')
        # paths[src_by_char] = {
        #     'get': {
        #         'summary': f'{src_title}Characteristics',
        #         'description': ('returns all characteristics of the given '
        #                         'type for the specified feature'),
        #         'tags': [src_id],
        #         'operationId': f'{src_title}Characteristics',
        #         'parameters': [
        #             {'$ref': '#/components/parameters/featureId'},
        #             {'$ref': '#/components/parameters/characteristicType'},
        #             {'$ref': '#/components/parameters/characteristicId'}
        #         ],
        #         'responses': RESPONSES
        #     }
        # }

        src_by_basin = url_join('/', src_by_feature, 'basin')
        paths[src_by_basin] = {
            'get': {
                'summary': f'{src_title}Basin',
                'description': ('returns the aggregated basin for the '
                                'specified feature in WGS84 lat/lon GeoJSON'),
                'tags': [src_id],
                'operationId': f'{src_title}Basin',
                'parameters': [
                    *parameters,
                    {'$ref': '#/components/parameters/simplified'},
                    {'$ref': '#/components/parameters/splitCatchment'}
                ],
                'responses': {
                    '200': {
                        'description': 'OK',
                        'content': {
                            'application/json': {
                                'schema': {
                                    '$ref': '#/components/schemas/FeatureCollection'  # noqa
                                }
                            },
                            'application/vnd.geo+json': {
                                'schema': {
                                    '$ref': '#/components/schemas/FeatureCollection'  # noqa
                                }
                            }
                        }
                    },
                    **RESPONSES
                }
            }
        }

        src_by_nav = url_join('/', src_by_feature, 'navigation')
        paths[src_by_nav] = {
            'get': {
                'summary': f'{src_title}NavigationOptions',
                'description': 'returns valid navigation end points',
                'tags': [src_id],
                'operationId': f'{src_title}NavigationOptions',
                'parameters': parameters,
                'responses': {
                    '200': {
                        'description': 'OK',
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'object',
                                    'additionalProperties': {
                                        'type': 'object'
                                    }
                                }
                            }
                        }
                    },
                    **RESPONSES
                }
            }
        }

        src_by_nav_md = url_join('/', src_by_nav, '{navigationMode}')
        paths[src_by_nav_md] = {
            'get': {
                'summary': f'{src_title}Navigation',
                'description': 'returns the navigation',
                'tags': [src_id],
                'operationId': f'{src_title}Navigation',
                'parameters': [
                    *parameters,
                    {'$ref': '#/components/parameters/navigationMode'}
                ],
                'responses': {
                    '200': {
                        'description': 'OK',
                        'content': {
                            'application/json': {
                                'schema': {
                                    '$ref': '#/components/schemas/DataSourceList'  # noqa
                                }
                            }
                        }
                    },
                    **RESPONSES
                }
            }
        }

        src_by_nav_ds = url_join('/', src_by_nav_md, '{dataSource}')
        paths[src_by_nav_ds] = {
            'get': {
                'summary': f'{src_title}NavigationDataSource',
                'description': ('returns all features found along the '
                                'specified navigation as points in WGS84 '
                                'lat/lon GeoJSON'),
                'tags': [src_id],
                'operationId': f'{src_title}NavigationDataSource',
                'parameters': [
                    *parameters,
                    {'$ref': '#/components/parameters/navigationMode'},
                    {
                        'name': 'dataSource',
                        'in': 'path',
                        'required': True,
                        'schema': {
                            'type': 'string',
                            'example': 'nwissite',
                            'enum': _sources
                        }
                    },
                    {'$ref': '#/components/parameters/distance'}
                ],
                'responses': {
                    '200': {
                        'description': 'OK',
                        'content': {
                            'application/json': {
                                'schema': {
                                    '$ref': '#/components/schemas/FeatureCollection'  # noqa
                                }
                            },
                            'application/vnd.geo+json': {
                                'schema': {
                                    '$ref': '#/components/schemas/FeatureCollection'  # noqa
                                }
                            },
                            'application/ld+json': {
                                'schema': {
                                    '$ref': '#/components/schemas/FeatureCollection'  # noqa
                                }
                            }
                        }
                    },
                    **RESPONSES
                }
            }
        }

        extra = []
        if src_id != 'comid':
            extra = [{'$ref': '#/components/parameters/trimStart'},
                     {'$ref': '#/components/parameters/trimTolerance'}]

        src_by_nav_fl = url_join('/', src_by_nav_md, 'flowlines')
        paths[src_by_nav_fl] = {
            'get': {
                'summary': f'{src_title}NavigationFlowlines',
                'description': ('returns the flowlines for the specified '
                                'navigation in WGS84 lat/lon GeoJSON'),
                'tags': [src_id],
                'operationId': f'{src_title}NavigationFlowlines',
                'parameters': [
                    *parameters,
                    {'$ref': '#/components/parameters/navigationMode'},
                    {'$ref': '#/components/parameters/distance'},
                    *extra
                ],
                'responses': {
                    '200': {
                        'description': 'OK',
                        'content': {
                            'application/json': {
                                'schema': {
                                    '$ref': '#/components/schemas/FeatureCollection'  # noqa
                                }
                            },
                            'application/vnd.geo+json': {
                                'schema': {
                                    '$ref': '#/components/schemas/FeatureCollection'  # noqa
                                }
                            },
                            'application/ld+json': {
                                'schema': {
                                    '$ref': '#/components/schemas/FeatureCollection'  # noqa
                                }
                            }
                        }
                    },
                    **RESPONSES
                }
            }
        }

    oas['paths'] = paths
    oas['tags'] = tags

    return oas


def generate_openapi_document(cfg_file: Union[Path, io.TextIOWrapper],
                              output_format: OAPIFormat):
    """
    Generate an OpenAPI document from the configuration file

    :param cfg_file: configuration Path instance
    :param output_format: output format for OpenAPI document

    :returns: content of the OpenAPI document in the output
              format requested
    """
    if isinstance(cfg_file, Path):
        with cfg_file.open(mode='r') as cf:
            s = yaml_load(cf)
    else:
        s = yaml_load(cfg_file)
    pretty_print = s['server'].get('pretty_print', False)

    if output_format == 'yaml':
        content = yaml.safe_dump(
            get_oas(s), default_flow_style=False, sort_keys=False)
    else:
        content = to_json(get_oas(s), pretty=pretty_print)
    return content


@click.group()
def openapi():
    """OpenAPI management"""
    pass


@click.command()
@click.pass_context
@click.argument('config_file', type=click.File(encoding='utf-8'))
@click.option('--format', '-f', 'format_', type=click.Choice(['json', 'yaml']),  # noqa
              default='yaml', help='output format (json|yaml)')
@click.option('--output-file', '-of', type=click.File('w', encoding='utf-8'),  # noqa
              help='Name of output file')
def generate(ctx, config_file, output_file, format_='yaml'):
    """Generate OpenAPI Document"""

    if config_file is None:
        raise click.ClickException('--config/-c required')

    content = generate_openapi_document(config_file, format_)

    if output_file is None:
        click.echo(content)
    else:
        click.echo(f'Generating {output_file.name}')
        output_file.write(content)
        click.echo('Done')


openapi.add_command(generate)
