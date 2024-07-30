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

import logging
from copy import deepcopy
from http import HTTPStatus
from typing import Any, Tuple, Union

from pygeoapi.api import F_HTML, F_JSON, F_JSONLD, FORMAT_TYPES, APIRequest
from pygeoapi.util import get_base_url, render_j2_template

from nldi import __version__
from nldi.functions import Functions
from nldi.log import setup_logger
from nldi.lookup.base import ProviderConnectionError, ProviderItemNotFoundError, ProviderQueryError
from nldi.lookup.catchment import CatchmentLookup
from nldi.lookup.flowline import FlowlineLookup
from nldi.lookup.pygeoapi import PygeoapiLookup
from nldi.lookup.source import CrawlerSourceLookup
from nldi.plugin import load_plugin
from nldi.util import TEMPLATES, sort_sources, stream_j2_template, to_json, url_join

LOGGER = logging.getLogger(__name__)
HEADERS = {"force_type": "application/json", "X-Powered-By": f"nldi {__version__}"}
FORMAT_TYPES.move_to_end(F_JSON, last=False)
SPLIT_CATCHMENT_THRESHOLD = 200


def pre_process(func):
    """
    Transform an incoming Request instance specific to the web framework into a generic.

    :class:`APIRequest` instance.
    :param func: decorated function
    :returns: `func`
    """
    def inner(*args):
        cls, req_in = args[:2]
        req_out = APIRequest.with_data(req_in, ["en-US"])
        if len(args) > 2:
            return func(cls, req_out, *args[2:])
        else:
            return func(cls, req_out)
            
    return inner


class API:
    """API object"""

    _nldi_data_crawler_source = None
    _nhdplus_catchment_lookup = None
    _nhdplus_flowline_lookup = None
    _pygeoapi_lookup = None

    def __init__(self, cfg):
        """
        constructor

        :param cfg: cfg dict

        :returns: `nldi.API` instance
        """
        self.config = cfg
        self.api_headers = HEADERS
        self.base_url = get_base_url(self.config)

        if "templates" not in self.config["server"]:
            self.config["server"]["templates"] = {"path": TEMPLATES}

        if "pretty_print" not in self.config["server"]:
            self.config["server"]["pretty_print"] = False

        self.pretty_print = self.config["server"]["pretty_print"]

        setup_logger(cfg["logging"])

        self.func = Functions(self.connection_def)

    def load_plugin(self, plugin_name: str, **kwargs) -> Any:
        """
        Provide copy of database connection configuration

        :param puglin_name: Name of plugin to load
        """
        return load_plugin({"name": plugin_name, "database": self.connection_def, "base_url": self.base_url, **kwargs})

    @property
    def connection_def(self) -> dict:
        """Provide copy of database connection configuration"""
        return deepcopy(self.config["server"]["data"])

    @property
    def crawler_source(self) -> CrawlerSourceLookup:
        """Crawler Source Database Provider"""
        if self._nldi_data_crawler_source is None:
            self._nldi_data_crawler_source = self.load_plugin("CrawlerSourceLookup")
        return self._nldi_data_crawler_source

    @property
    def catchment_lookup(self) -> CatchmentLookup:
        """Catchment Lookup Database Provider"""
        if self._nhdplus_catchment_lookup is None:
            self._nhdplus_catchment_lookup = self.load_plugin("CatchmentLookup")
        return self._nhdplus_catchment_lookup

    @property
    def flowline_lookup(self) -> FlowlineLookup:
        """Flowline Lookup Database Provider"""
        if self._nhdplus_flowline_lookup is None:
            self._nhdplus_flowline_lookup = self.load_plugin("FlowlineLookup")
        return self._nhdplus_flowline_lookup

    @property
    def pygeoapi_lookup(self) -> PygeoapiLookup:
        """pygeoapi Lookup Provider"""
        if self._pygeoapi_lookup is None:
            try:
                PYGEOAPI_URL = self.config["pygeoapi"]["gdp_url"]
            except KeyError:
                PYGEOAPI_URL = "https://labs.waterdata.usgs.gov/api/nldi/pygeoapi"  # noqa
            self._pygeoapi_lookup = self.load_plugin(
                "PygeoapiLookup", catchment_lookup=self.catchment_lookup, pygeoapi_url=PYGEOAPI_URL
            )
        return self._pygeoapi_lookup

    @pre_process
    def landing_page(self, request: Union[APIRequest, Any]) -> Tuple[dict, int, str]:
        """
        Provide API landing page

        :param request: A reaquest object

        :returns: tuple of headers, status code, content
        """
        if not request.is_valid():
            return self.get_exception(request)

        headers = request.get_response_headers(**HEADERS)
        content = {
            "title": self.config["metadata"]["identification"]["title"],
            "description": self.config["metadata"]["identification"]["description"],  # noqa
            "links": [
                {"rel": "data", "type": "application/json", "title": "Sources", "href": f"{self.base_url}/linked-data"},
                {
                    "rel": "service-desc",
                    "type": "text/html",
                    "title": "The OpenAPI definition as HTML",
                    "href": f"{self.base_url}/openapi?f=html",
                },
                {
                    "rel": "service-desc",
                    "type": "application/vnd.oai.openapi+json;version=3.0",
                    "title": "The OpenAPI definition as JSON",
                    "href": f"{self.base_url}/openapi?f=json",
                },
            ],
        }

        try:
            if self.config["pygeoapi"]["enabled"] is True:
                content["links"].append(
                    {
                        "rel": "data",
                        "type": "text/html",
                        "title": "pygeoapi for the NLDI",
                        "href": f"{self.base_url}/pygeoapi?f=html",
                    }
                )
        except KeyError:
            LOGGER.debug("Omitting pygeoapi link")

        return headers, HTTPStatus.OK, to_json(content, self.pretty_print)

    @pre_process
    def get_openapi(self, request: Union[APIRequest, Any], openapi: dict) -> Tuple[dict, int, str]:
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
            headers["Content-Type"] = "text/html"
            template = "openapi/swagger.html"
            if request._args.get("ui") == "redoc":
                template = "openapi/redoc.html"

            path = f"{self.base_url}/openapi"
            data = {"openapi-document-path": path}
            content = render_j2_template(self.config, template, data, request.locale)
            return headers, HTTPStatus.OK, content

        headers["Content-Type"] = "application/vnd.oai.openapi+json;version=3.0"  # noqa

        if isinstance(openapi, dict):
            return headers, HTTPStatus.OK, to_json(openapi, self.pretty_print)
        else:
            return headers, HTTPStatus.OK, openapi

    @pre_process
    def get_crawler_sources(self, request: Union[APIRequest, Any]) -> Tuple[dict, int, str]:
        """
        Provide crawler source table

        :param request: A request object

        :returns: tuple of headers, status code, content
        """

        if not request.is_valid():
            return self.get_exception(request)

        headers = request.get_response_headers(**HEADERS)

        content = [
            {
                "source": "comid",
                "sourceName": "NHDPlus comid",
                "features": url_join(self.base_url, "linked-data/comid/position"),
            }
        ]

        try:
            sources = self.crawler_source.query()
        except ProviderConnectionError:
            msg = "connection error (check logs)"
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )
        except ProviderQueryError:
            msg = "query error (check logs)"
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )

        for source in sort_sources(sources):
            src_id = source["source_suffix"]
            content.append(
                {
                    "source": src_id,
                    "sourceName": source["source_name"],
                    "features": url_join(self.base_url, "linked-data", src_id.lower()),
                }
            )

        return headers, HTTPStatus.OK, to_json(content, self.pretty_print)

    @pre_process
    def get_comid_by_id(self, request: Union[APIRequest, Any], identifier: str) -> Tuple[dict, int, str]:
        """
        Provide NHDPv2 comid by id

        :param request: A request object
        :param identifier: NHDPv2 comid

        :returns: tuple of headers, status code, content
        """

        if not request.is_valid():
            return self.get_exception(request)

        headers = request.get_response_headers(**HEADERS)

        try:
            feature = self.flowline_lookup.get(identifier)
            features = [
                feature,
            ]
        except ProviderConnectionError:
            msg = "connection error (check logs)"
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )
        except ProviderQueryError:
            msg = "query error (check logs)"
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )
        except ProviderItemNotFoundError:
            msg = f"No comid found for {identifier}"
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )

        content = stream_j2_template("FeatureCollection.j2", features)
        return headers, HTTPStatus.OK, content

    @pre_process
    def get_hydrolocation(self, request: Union[APIRequest, Any]) -> Tuple[dict, int, str]:
        """
        Provide hydrologic location by feature intersect

        :param request: A request object

        :returns: tuple of headers, status code, content
        """

        if not request.is_valid():
            return self.get_exception(request)

        headers = request.get_response_headers(**HEADERS)

        try:
            coords = request.params["coords"]
        except KeyError:
            msg = "Required request parameter 'coords' is not present."
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )

        try:
            feature = self.pygeoapi_lookup.get_hydrolocation(coords)
        except ProviderConnectionError:
            msg = "connection error (check logs)"
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )
        except ProviderQueryError:
            msg = "query error (check logs)"
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )
        except ProviderItemNotFoundError:
            msg = f"No comid found at {coords}"
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )

        return headers, HTTPStatus.OK, to_json(feature, self.pretty_print)

    @pre_process
    def get_comid_by_position(self, request: Union[APIRequest, Any]) -> Tuple[dict, int, str]:
        """
        Provide NHDPv2 comid by location

        :param request: A request object

        :returns: tuple of headers, status code, content
        """

        if not request.is_valid():
            return self.get_exception(request)

        headers = request.get_response_headers(**HEADERS)

        try:
            coords = request.params["coords"]
        except KeyError:
            msg = "Required request parameter 'coords' is not present."
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )

        try:
            identifier = self.catchment_lookup.query(coords)
        except ProviderConnectionError:
            msg = "connection error (check logs)"
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )
        except ProviderQueryError:
            msg = "query error (check logs)"
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )
        except ProviderItemNotFoundError:
            msg = f"No comid found at {coords}"
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )

        try:
            feature = self.flowline_lookup.get(identifier)
            features = [
                feature,
            ]
        except ProviderQueryError:
            msg = "query error (check logs)"
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )
        except ProviderItemNotFoundError:
            msg = f"No comid found at {coords}"
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )

        content = stream_j2_template("FeatureCollection.j2", features)
        return headers, HTTPStatus.OK, content

    @pre_process
    def get_source_features(
        self, request: Union[APIRequest, Any], source_name: str, identifier: str
    ) -> Tuple[dict, int, str]:
        """
        Provide Crawled Features

        :param request: A request object
        :param source_name: NLDI Source name
        :param identifier: NLDI Source feature identifier

        :returns: tuple of headers, status code, content
        """
        if not request.is_valid():
            return self.get_exception(request)

        headers = request.get_response_headers(**HEADERS)

        source_name = source_name.lower()
        try:
            source = self.crawler_source.get(source_name)
        except ProviderConnectionError:
            msg = "connection error (check logs)"
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )
        except ProviderQueryError:
            msg = "query error (check logs)"
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )
        except ProviderItemNotFoundError:
            msg = f"The feature source '{source_name}' does not exist."
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )

        plugin = self.load_plugin("FeatureLookup", source=source)
        if identifier:
            try:
                feature = plugin.get(identifier)
                features = [
                    feature,
                ]
            except ProviderQueryError:
                msg = "query error (check logs)"
                return self.get_exception(
                    HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
                )
            except ProviderItemNotFoundError:
                msg = f"The source '{source_name}' has no item {identifier}."
                return self.get_exception(
                    HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
                )

        else:
            try:
                features = plugin.query()
            except ProviderQueryError:
                msg = "query error (check logs)"
                return self.get_exception(
                    HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
                )
            except ProviderItemNotFoundError:
                msg = f"The source '{source_name}' has not been crawled."
                return self.get_exception(
                    HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
                )

        if request.format == F_JSONLD:
            if identifier:
                content = stream_j2_template("FeatureGraph.j2", features)
            else:
                content = stream_j2_template("FeatureCollectionGraph.j2", features)  # noqa
        else:
            content = stream_j2_template("FeatureCollection.j2", features)

        return headers, HTTPStatus.OK, content

    @pre_process
    def get_basin(self, request: Union[APIRequest, Any], source_name: str, identifier: str) -> Tuple[dict, int, str]:
        """
        Provide Basin information

        :param request: A request object
        :param source_name: NLDI source name
        :param identifier: NLDI Source feature identifier

        :returns: tuple of headers, status code, content
        """
        if not request.is_valid():
            return self.get_exception(request)

        headers = request.get_response_headers(**HEADERS)

        source_name = source_name.lower()
        try:
            if source_name != "comid":
                source = self.crawler_source.get(source_name)
                plugin = self.load_plugin("FeatureLookup", source=source)
                feature = plugin.get(identifier)
                start_comid = int(feature["properties"]["comid"])
                isPoint = feature["geometry"]["type"] == "Point"
            else:
                self.flowline_lookup.get(identifier)
                start_comid = int(identifier)
                isPoint = False
        except ProviderConnectionError:
            msg = "connection error (check logs)"
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )
        except ProviderQueryError:
            msg = "query error (check logs)"
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )
        except ProviderItemNotFoundError:
            msg = f"The feature {identifier} does not exist for '{source_name}'."  # noqa
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )

        _ = request.params.get("simplified", "True").lower() == "true"
        simplified = _

        _ = request.params.get("splitCatchment", "False").lower() == "true"
        splitCatchment = _

        if isPoint and splitCatchment:
            LOGGER.debug("Performing Split Catchment")
            point = self.func.get_point(identifier, source_name)

            if point is None:
                distance = self.func.get_distance(identifier, source_name)
                LOGGER.debug(distance)

                if distance <= SPLIT_CATCHMENT_THRESHOLD:
                    point = self.func.get_closest(identifier, source_name)
                else:
                    [lon, lat] = feature["geometry"]["coordinates"]
                    wkt_geom = f"POINT({lon} {lat})"
                    response = self.pygeoapi_lookup.get_hydrolocation(wkt_geom)
                    point = response["features"][0]["geometry"]["coordinates"]

            if point is None:
                msg = "Unable to retrieve point on flowline for catchment splitting."  # noqa
                return self.get_exception(
                    HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
                )

            [lon, lat] = point
            wkt_geom = f"POINT({lon} {lat})"
            features = self.pygeoapi_lookup.get_split_catchment(wkt_geom)
        else:
            LOGGER.debug(f"Returning with simplified geometry: {simplified}")
            features = self.func.get_basin(start_comid, simplified)

        content = stream_j2_template("FeatureCollection.j2", features)
        return headers, HTTPStatus.OK, content

    @pre_process
    def get_navigation_info(
        self, request: Union[APIRequest, Any], source_name: str, identifier: str, nav_mode: str
    ) -> Tuple[dict, int, str]:
        """
        Provide Navigation information

        :param request: A request object
        :param source_name: NLDI source name
        :param identifier: NLDI Source feature identifier
        :param nav_mode: NLDI Navigation mode

        :returns: tuple of headers, status code, content
        """
        if not request.is_valid():
            return self.get_exception(request)

        headers = request.get_response_headers(**HEADERS)

        source_name = source_name.lower()
        try:
            if source_name != "comid":
                self.crawler_source.get(source_name)
        except ProviderConnectionError:
            msg = "connection error (check logs)"
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )
        except ProviderQueryError:
            msg = "query error (check logs)"
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )
        except ProviderItemNotFoundError:
            msg = f"The feature source '{source_name}' does not exist."
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )

        nav_url = url_join(self.base_url, "linked-data", source_name, identifier, "navigation")
        if nav_mode is None:
            content = {
                "upstreamMain": url_join(nav_url, "UM"),
                "upstreamTributaries": url_join(nav_url, "UT"),
                "downstreamMain": url_join(nav_url, "DM"),
                "downstreamDiversions": url_join(nav_url, "DD"),
            }

            return headers, HTTPStatus.OK, to_json(content, self.pretty_print)

        content = [
            {
                "source": "Flowlines",
                "sourceName": "NHDPlus flowlines",
                "features": url_join(nav_url, nav_mode, "flowlines"),
            }
        ]

        try:
            sources = self.crawler_source.query()
        except ProviderQueryError:
            msg = "query error (check logs)"
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )

        for source in sort_sources(sources):
            src_id = source["source_suffix"]
            content.append(
                {
                    "source": src_id,
                    "sourceName": source["source_name"],
                    "features": url_join(nav_url, nav_mode, src_id.lower()),
                }
            )

        return headers, HTTPStatus.OK, to_json(content, self.pretty_print)

    @pre_process
    def get_flowlines(
        self, request: Union[APIRequest, Any], source_name: str, identifier: str, nav_mode: str
    ) -> Tuple[dict, int, str]:
        """
        Provide navigation query

        :param request: A request object
        :param source_name: NLDI source name
        :param identifier: NLDI Source feature identifier
        :param nav_mode: NLDI Navigation mode

        :returns: tuple of headers, status code, content
        """
        if not request.is_valid():
            return self.get_exception(request)

        headers = request.get_response_headers(**HEADERS)

        start_comid = None
        source_name = source_name.lower()

        if source_name == "comid":
            try:
                self.flowline_lookup.get(identifier)
            except ProviderQueryError:
                msg = "query error (check logs)"
                return self.get_exception(
                    HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
                )
            except ProviderItemNotFoundError:
                msg = f"The comid source '{identifier}' does not exist."
                return self.get_exception(
                    HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
                )

            start_comid = int(identifier)

        else:
            try:
                source = self.crawler_source.get(source_name)
            except ProviderItemNotFoundError:
                msg = f"The feature source '{source_name}' does not exist."
                return self.get_exception(
                    HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
                )

            plugin = self.load_plugin("FeatureLookup", source=source)
            try:
                feature = plugin.get(identifier)
                start_comid = int(feature["properties"]["comid"])
            except ProviderQueryError:
                msg = "query error (check logs)"
                return self.get_exception(
                    HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
                )
            except (KeyError, IndexError):
                msg = f"The feature {identifier} from source '{source_name}' is not indexed."  # noqa
                return self.get_exception(
                    HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
                )
            except ProviderItemNotFoundError:
                msg = f"The source '{source_name}' has no item {identifier}."
                return self.get_exception(
                    HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
                )

        try:
            distance = float(request.params["distance"])
        except KeyError:
            msg = "Required request parameter 'distance' is not present."
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )
        except ValueError:
            msg = "Required request parameter 'distance' must be a number."
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )

        LOGGER.debug(f"Doing navigation {nav_mode} for {distance}")
        nav = self.func.get_navigation(nav_mode, start_comid, distance)

        trim_start = False
        try:
            trim_start = str(request.params["trimStart"]).lower() == "true"
        except (KeyError, TypeError):
            if request.params.get("trimStart"):
                msg = "Request parameter 'trimStart' must be a boolean."
                return self.get_exception(
                    HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
                )

        LOGGER.debug(trim_start)
        if trim_start is True:
            try:
                trim_tolerance = request.params.get("trimTolerance", 0)
                trim_tolerance = float(trim_tolerance)
            except ValueError:
                msg = "Request parameter 'trimTolerance' must be a number."
                return self.get_exception(
                    HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
                )

            LOGGER.debug(f"Trimming flowline with tolerance: {trim_tolerance}")
            try:
                measure = feature["properties"]["measure"]
                if not measure:
                    measure = self.func.estimate_measure(identifier, source_name)
                measure = float(measure)
                LOGGER.debug(f"measure {measure}")
            except KeyError:
                msg = "Required field 'measure' is not present."
                return self.get_exception(
                    HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
                )
            except ValueError:
                msg = "Required field 'measure' must be a number."
                return self.get_exception(
                    HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
                )

            trim_nav = self.func.trim_navigation(nav_mode, start_comid, trim_tolerance, measure)
            features = self.flowline_lookup.trim_navigation(nav, trim_nav)
        else:
            features = self.flowline_lookup.lookup_navigation(nav)

        content = stream_j2_template("FeatureCollection.j2", features)

        return headers, HTTPStatus.OK, content

    @pre_process
    def get_navigation(
        self, request: Union[APIRequest, Any], source_name: str, identifier: str, nav_mode: str, data_source: str
    ) -> Tuple[dict, int, str]:
        """
        Provide navigation query

        :param request: A request object
        :param source_name: NLDI source name
        :param identifier: NLDI Source feature identifier
        :param nav_mode: NLDI Navigation mode
        :param data_source: NLDI output source_name

        :returns: tuple of headers, status code, content
        """
        if not request.is_valid():
            return self.get_exception(request)

        headers = request.get_response_headers(**HEADERS)

        start_comid = None
        source_name = source_name.lower()

        if source_name == "comid":
            try:
                self.flowline_lookup.get(identifier)
            except ProviderQueryError:
                msg = "query error (check logs)"
                return self.get_exception(
                    HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
                )
            except ProviderItemNotFoundError:
                msg = f"The comid source '{identifier}' does not exist."
                return self.get_exception(
                    HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
                )

            start_comid = int(identifier)

        else:
            try:
                source = self.crawler_source.get(source_name)
            except ProviderItemNotFoundError:
                msg = f"The feature source '{source_name}' does not exist."
                return self.get_exception(
                    HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
                )

            plugin = self.load_plugin("FeatureLookup", source=source)
            try:
                feature = plugin.get(identifier)
                start_comid = int(feature["properties"]["comid"])
            except ProviderQueryError:
                msg = "query error (check logs)"
                return self.get_exception(
                    HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
                )
            except (KeyError, IndexError):
                msg = f"The feature {identifier} from source '{source_name}' is not indexed."  # noqa
                return self.get_exception(
                    HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
                )
            except ProviderItemNotFoundError:
                msg = f"The source '{source_name}' has no item {identifier}."
                return self.get_exception(
                    HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
                )

        source2_name = data_source.lower()
        try:
            source2 = self.crawler_source.get(source2_name)
            plugin = self.load_plugin("FeatureLookup", source=source2)
        except ProviderQueryError:
            msg = "query error (check logs)"
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )
        except ProviderItemNotFoundError:
            msg = f"The feature source '{source2_name}' does not exist."
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )

        try:
            distance = float(request.params["distance"])
        except KeyError:
            msg = "Required request parameter 'distance' is not present."
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )
        except ValueError:
            msg = "Required request parameter 'distance' must be a number."
            return self.get_exception(
                HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
            )

        nav_results = self.func.get_navigation(nav_mode, start_comid, distance)
        features = plugin.lookup_navigation(nav_results)

        if request.format == F_JSONLD:
            content = stream_j2_template("FeatureCollectionGraph.j2", features)
        else:
            content = stream_j2_template("FeatureCollection.j2", features)

        return headers, HTTPStatus.OK, content

    def get_exception(self, status, headers, format_, code, description) -> Tuple[dict, int, str]:
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
        exception = {"code": code, "description": description}

        content = to_json(exception, self.pretty_print)

        return headers, status, content
