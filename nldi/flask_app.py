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

from flask import (Blueprint, Flask, request,
                   stream_with_context, Response, send_from_directory)
from jinja2.environment import TemplateStream
import logging
import os

from nldi.api import API
from nldi.util import yaml_load

LOGGER = logging.getLogger(__name__)


if 'NLDI_CONFIG' not in os.environ:
    raise RuntimeError('NLDI_CONFIG environment variable not set')

with open(os.environ.get('NLDI_CONFIG'), encoding='utf8') as fh:
    CONFIG = yaml_load(fh)

STATIC_FOLDER = 'static'
if 'templates' in CONFIG['server']:
    STATIC_FOLDER = CONFIG['server']['templates'].get('static', 'static')


APP = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path='/static')
APP.url_map.strict_slashes = False
BLUEPRINT = Blueprint('nldi', __name__, static_folder=STATIC_FOLDER)

API_ = API(CONFIG)


def get_response(result: tuple):
    """
    Creates a Flask Response object and updates matching headers.
    :param result: The result of the API call.
                   This should be a tuple of (headers, status, content).
    :returns: A Response instance.
    """

    headers, status, content = result
    if isinstance(content, TemplateStream):
        response = Response(stream_with_context(content), status)
    else:
        response = Response(content, status)

    if headers:
        response.headers = headers
    return response


@BLUEPRINT.route('/favicon.ico')
def favicon():
    return send_from_directory(STATIC_FOLDER, 'favicon.ico',
                               mimetype='image/vnd.microsoft.icon')


@BLUEPRINT.route('/')
def home():
    """
    Root endpoint

    :returns: HTTP response
    """
    return get_response(API_.landing_page(request))


@BLUEPRINT.route('/openapi')
def openapi():
    """
    OpenAPI endpoint

    :returns: HTTP response
    """
    with open(os.environ.get('NLDI_OPENAPI'), encoding='utf8') as ff:
        if os.environ.get('NLDI_OPENAPI').endswith(('.yaml', '.yml')):
            openapi_ = yaml_load(ff)
        else:  # JSON string, do not transform
            openapi_ = ff.read()

    return get_response(API_.get_openapi(request, openapi_))


@BLUEPRINT.route('/linked-data')
def sources():
    """
    Data sources endpoint

    :returns: HTTP response
    """
    return get_response(API_.get_crawler_sources(request))


@BLUEPRINT.route('/linked-data/hydrolocation')
def hydrolocation():
    """
    Hydrolocation endpoint

    :returns: HTTP response
    """
    return get_response(API_.get_hydrolocation(request))


@BLUEPRINT.route('/linked-data/comid/position')
def get_comid_by_position():
    """
    NHDPv2 comid by position endpoint

    :returns: HTTP response
    """
    return get_response(API_.get_comid_by_position(request))


@BLUEPRINT.route('/linked-data/comid/<int:comid>')
def get_comid_by_id(comid=None):
    """
    NHDPv2 comid by id endpoint

    :returns: HTTP response
    """
    return get_response(API_.get_comid_by_id(request, comid))


@BLUEPRINT.route('/linked-data/<path:source_name>')
@BLUEPRINT.route('/linked-data/<path:source_name>/<path:identifier>')
def get_source_features(source_name=None, identifier=None):
    """
    Data source endpoint

    :param source_name: NLDI source name
    :param identifier: NLDI Source feature identifier

    :returns: HTTP response
    """
    return get_response(
        API_.get_source_features(request, source_name, identifier))


@BLUEPRINT.route('/linked-data/<path:source_name>/<path:identifier>/basin')
def get_basin(source_name=None, identifier=None):
    """
    Basin lookup endpoint

    :param source_name: NLDI source name
    :param identifier: NLDI Source feature identifier

    :returns: HTTP response
    """
    return get_response(
        API_.get_basin(request, source_name, identifier))


@BLUEPRINT.route('/linked-data/<path:source_name>/<path:identifier>/navigation')  # noqa
@BLUEPRINT.route('/linked-data/<path:source_name>/<path:identifier>/navigation/<path:nav_mode>')  # noqa
def get_navigation_info(source_name=None, identifier=None, nav_mode=None):
    """
    Data source navigation information endpoint

    :param source_name: NLDI source name
    :param identifier: NLDI Source feature identifier
    :param nav_mode: NLDI Navigation mode

    :returns: HTTP response
    """
    return get_response(
        API_.get_navigation_info(request, source_name, identifier, nav_mode))


@BLUEPRINT.route('/linked-data/<path:source_name>/<path:identifier>/navigation/<path:nav_mode>/flowlines')  # noqa
def get_flowline_navigation(source_name=None, identifier=None, nav_mode=None):  # noqa
    """
    Data source flowline navigation endpoint

    :param source_name: NLDI input source name
    :param identifier: NLDI Source feature identifier
    :param nav_mode: NLDI Navigation mode

    :returns: HTTP response
    """
    return get_response(API_.get_flowlines(
        request, source_name, identifier, nav_mode))


@BLUEPRINT.route('/linked-data/<path:source_name>/<path:identifier>/navigation/<path:nav_mode>/<path:data_source>')  # noqa
def get_navigation(source_name=None, identifier=None, nav_mode=None, data_source=None):  # noqa
    """
    Data source navigation endpoint

    :param source_name: NLDI input source name
    :param identifier: NLDI Source feature identifier
    :param nav_mode: NLDI Navigation mode
    :param data_source: NLDI output source name

    :returns: HTTP response
    """
    return get_response(API_.get_navigation(
        request, source_name, identifier, nav_mode, data_source))


if CONFIG['server']['pygeoapi'] is True:
    from pygeoapi.flask_app import BLUEPRINT as PYGEOAPI_BLUEPRINT
    APP.register_blueprint(PYGEOAPI_BLUEPRINT, url_prefix='/pygeoapi')

APP.register_blueprint(BLUEPRINT)
