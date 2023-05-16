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

from flask import Blueprint, Flask, make_response, request
import logging
import os

from pygeoapi.util import yaml_load

from nldi.api import API

LOGGER = logging.getLogger(__name__)


if 'NLDI_CONFIG' not in os.environ:
    raise RuntimeError('NLDI_CONFIG environment variable not set')

with open(os.environ.get('NLDI_CONFIG'), encoding='utf8') as fh:
    CONFIG = yaml_load(fh)

STATIC_FOLDER = 'static'
if 'templates' in CONFIG['server']:
    STATIC_FOLDER = CONFIG['server']['templates'].get('static', 'static')


APP = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path='/static')
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
    response = make_response(content, status)

    if headers:
        response.headers = headers
    return response


@BLUEPRINT.route('/')
def home():
    """
    OpenAPI endpoint
    :returns: HTTP response
    """
    return get_response(API_.landing_page(request))


@BLUEPRINT.route('/linked-data')
def sources():
    """
    OpenAPI endpoint
    :returns: HTTP response
    """
    return get_response(API_.get_sources(request))


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


APP.register_blueprint(BLUEPRINT)
