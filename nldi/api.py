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

from http import HTTPStatus
import logging
from typing import Any, Tuple, Union

from pygeoapi.api import APIRequest, FORMAT_TYPES, F_HTML, F_JSON
from pygeoapi.util import get_base_url, render_j2_template, url_join

from nldi import __version__
from nldi.log import setup_logger
from nldi.util import TEMPLATES, sort_sources, to_json

LOGGER = logging.getLogger(__name__)
HEADERS = {
    'force_type': 'application/json',
    'X-Powered-By': f'nldi {__version__}'
}
FORMAT_TYPES.move_to_end(F_JSON, last=False)


def pre_process(func):
    """
    Decorator that transforms an incoming Request instance specific to the
    web framework (i.e. Flask, Starlette or Django) into a generic

    :class:`APIRequest` instance.

    :param func: decorated function

    :returns: `func`
    """

    def inner(*args):
        cls, req_in = args[:2]
        req_out = APIRequest.with_data(req_in, ['en-US'])
        if len(args) > 2:
            return func(cls, req_out, *args[2:])
        else:
            return func(cls, req_out)

    return inner


class API:
    """API object"""

    def __init__(self, cfg):
        """
        constructor

        :param cfg: cfg dict

        :returns: `nldi.API` instance
        """
        self.config = cfg
        self.api_headers = HEADERS
        self.base_url = get_base_url(self.config)

        if 'templates' not in self.config['server']:
            self.config['server']['templates'] = {'path': TEMPLATES}

        if 'pretty_print' not in self.config['server']:
            self.config['server']['pretty_print'] = False

        self.pretty_print = self.config['server']['pretty_print']

        setup_logger(cfg['logging'])

        self.base_url = get_base_url(cfg)

    @pre_process
    def landing_page(self, request: Union[APIRequest, Any]
                     ) -> Tuple[dict, int, str]:
        """
        Provide API landing page
        :param request: A reaquest object
        :returns: tuple of headers, status code, content
        """
        if not request.is_valid():
            return self.get_exception(request)

        headers = request.get_response_headers(**HEADERS)
        content = {
            'title': self.config['metadata']['identification']['title'],
            'description': self.config['metadata']['identification']['description'],  # noqa
            'links': [{
                'rel': 'service-desc',
                'type': 'application/vnd.oai.openapi+json;version=3.0',
                'title': 'The OpenAPI definition as JSON',
                'href': f'{self.base_url}/openapi?f=json'
            }, {
                'rel': 'service-desc',
                'type': 'text/html',
                'title': 'The OpenAPI definition as HTML',
                'href': f'{self.base_url}/openapi?f=html'
            }, {
                'rel': 'data',
                'type': 'application/json',
                'title': 'Sources',
                'href': f'{self.base_url}/linked-data'
            }]
        }

        return headers, HTTPStatus.OK, to_json(content, self.pretty_print)

    @pre_process
    def get_openapi(self, request: Union[APIRequest, Any], openapi
                    ) -> Tuple[dict, int, str]:
        """
        Provide OpenAPI document

        :param request: A request object
        :param openapi: dict of OpenAPI definition

        :returns: tuple of headers, status code, content
        """

        if not request.is_valid():
            return self.get_format_exception(request)

        headers = request.get_response_headers(**HEADERS)

        if request.format == F_HTML:
            headers['Content-Type'] = 'text/html'
            template = 'openapi/swagger.html'
            if request._args.get('ui') == 'redoc':
                template = 'openapi/redoc.html'

            path = f'{self.base_url}/openapi'
            data = {
                'openapi-document-path': path
            }
            content = render_j2_template(self.config, template, data,
                                         request.locale)
            return headers, HTTPStatus.OK, content

        headers['Content-Type'] = 'application/vnd.oai.openapi+json;version=3.0'  # noqa

        if isinstance(openapi, dict):
            return headers, HTTPStatus.OK, to_json(openapi, self.pretty_print)
        else:
            return headers, HTTPStatus.OK, openapi

    @pre_process
    def get_sources(self, request: Union[APIRequest, Any]
                    ) -> Tuple[dict, int, str]:
        """
        Provide OpenAPI document

        :param request: A request object

        :returns: tuple of headers, status code, content
        """

        if not request.is_valid():
            return self.get_exception(request)

        headers = request.get_response_headers(**HEADERS)

        content = []
        for source in sort_sources(self.config['sources']):
            src_id = source['source_suffix']
            src = {
                'source': src_id,
                'sourceName': source['source_name'],
                'features': url_join(
                    self.base_url, 'linked-data', src_id.lower()
                )
            }
            content.append(src)

        return headers, HTTPStatus.OK, to_json(content, self.pretty_print)

    def get_exception(self, status, headers, format_, code,
                      description) -> Tuple[dict, int, str]:
        """
        Exception handler
        :param status: HTTP status code
        :param headers: dict of HTTP response headers
        :param format_: format string
        :param code: OGC API exception code
        :param description: OGC API exception code
        :returns: tuple of headers, status, and message
        """

        LOGGER.error(description)
        exception = {
            'code': code,
            'description': description
        }

        content = to_json(exception, self.pretty_print)

        return headers, status, content
