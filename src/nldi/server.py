#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#


"""Main entry point for launching the NLDI server."""

import http
import os
import sys
from typing import Any, Dict, List, Tuple

import flask
from flask_cors import CORS

# from pygeoapi.util import render_j2_template  ##TODO: can we drop this dependency? Need to figure out templating
from . import LOGGER, __version__, log, util
from .api.main import API
from .config import Configuration
from .querybuilder.lookup_query import estimate_measure
from .querybuilder.navigate_query import navigation as build_nav_query
from .querybuilder.navigate_query import trim_navigation as trim_nav_query

NLDI_API = None  ## Global -- this will be assigned inside the app factory later.

# region Preamble
log.initialize(LOGGER, level="DEBUG")
##TODO: The log level  should be a configurable option, perhaps set with -V or --verbose switch.

## Loading CONFIG here, after loggers and whatnot are set up.
if "NLDI_CONFIG" not in os.environ:
    raise RuntimeError("NLDI_CONFIG environment variable not set")
CONFIG = Configuration(os.environ.get("NLDI_CONFIG"))

LOGGER.info(f"NLDI v{__version__} API Server >> Starting Up")
log.versions(logger=LOGGER)

# region Routing
# Creates dispatch table for ROOT of the server endpoints:
ROOT = flask.Blueprint("nldi", __name__)


@ROOT.before_request
def log_incoming_request() -> None:
    """Implement simple middleware function to log requests."""
    LOGGER.debug(f"{flask.request.method} {flask.request.url}")
    # TODO: other pre-request activities can go here.

    ## Sets up a callback to update headers after the request is processed.
    @flask.after_this_request
    def update_headers(r: flask.Response) -> flask.Response:
        """Implement simple middlware function to update response headers."""
        r.headers.update(
            {
                "X-Powered-By": f"nldi {__version__}",
            }
            # TODO: add headers to this dict that you want in every response.
        )
        return r


@ROOT.route("/")
def home() -> flask.Response:
    """
    Root/home document for this web service.

    Returns a JSON document showing available services.

    :return: JSON
    :rtype: flask.Response
    """
    content = {
        "title": CONFIG["metadata"]["identification"]["title"],
        "description": CONFIG["metadata"]["identification"]["description"],
        "links": [
            {
                "rel": "data",
                "type": "application/json",
                "title": "Sources",
                "href": util.url_join(CONFIG["base_url"], "linked-data"),
            },
            {
                "rel": "service-desc",
                "type": "text/html",
                "title": "The OpenAPI definition as HTML",
                "href": util.url_join(CONFIG["base_url"], "openapi?f=html"),
            },
            {
                "rel": "service-desc",
                "type": "application/vnd.oai.openapi+json;version=3.0",
                "title": "The OpenAPI definition as JSON",
                "href": util.url_join(CONFIG["base_url"], "openapi?f=json"),
            },
        ],
    }
    return flask.jsonify(content)


@ROOT.route("/favicon.ico")
def favicon():
    """Send favicon file."""
    return flask.send_from_directory("./static/", "favicon.ico", mimetype="image/vnd.microsoft.icon")


@ROOT.route("/openapi")
def openapi_spec() -> Tuple[dict, int, str]:
    """
    Return the OpenAPI document spec using either the swagger or redoc UI.

    :param request: Incoming API request
    :type request: _type_
    """
    global NLDI_API
    if requested_format := flask.request.args.get("f", "html") == "html":
        if flask.request.args.get("ui") == "redoc":
            template = "openapi/redoc.html"
        else:
            template = "openapi/swagger.html"
        data = {"openapi-document-path": f"openapi"}  ##NOTE: intentionally using relative path here.

        content = util.render_j2_template(NLDI_API.config, template, data)
        return flask.Response(
            headers={"Content-Type": "text/html"},
            status=http.HTTPStatus.OK,
            response=content,
        )
    else:
        r = flask.jsonify(NLDI_API.openapi_json)
        r.headers["Content-Type"] = "application/vnd.oai.openapi+json;version=3.0"  # noqa
        return r


@ROOT.route("/about/health")
def healthcheck() -> flask.Response:
    """
    Simple healthcheck endpoint.

    HTTP code 200 signifies "up" status.  Any other response code indicates "DOWN".
    """
    global NLDI_API
    healthy = True
    try:
        healthy = NLDI_API.sources.db_is_alive()
    except Exception:
        healthy = False
    if healthy:
        return flask.jsonify({"status": "UP"})
    else:
        return flask.Response(status=http.HTTPStatus.SERVICE_UNAVAILABLE)


@ROOT.route("/about/info")
def aboutinfo() -> flask.Response:
    """Simple 'about' properties."""
    return flask.jsonify(
        {
            "name": "nldi-py",
            "version": __version__,
        }
    )


@ROOT.route("/linked-data")
def sources() -> flask.Response:
    """
    Linked Data Sources endpoint.

    This endpoint produces a list of available sources.

    :returns: HTTP response
    """
    global NLDI_API
    content = [
        {
            "source": "comid",
            "sourceName": "NHDPlus comid",
            "features": util.url_join(NLDI_API.config["base_url"], "linked-data", "comid", "position"),
        }
    ]  ## This source is hard-coded -- should always be available.  Other sources are loaded from the source table.
    for s in NLDI_API.sources.get_all():
        content.append(
            {
                "source": s["source_suffix"],
                "sourceName": s["source_name"],
                "features": util.url_join(NLDI_API.config["base_url"], "linked-data", s["source_suffix"].lower()),
            }
        )
    return flask.jsonify(content)


## THis route short-circuits the normal source lookup, and goes straight to the flowline plugin, which is specific to the 'comid' source.
@ROOT.route("/linked-data/comid/<int:comid>")
def get_flowline_by_comid(comid=None):
    """
    Find flowline(s) by attribute search on the COMID property.

    :param comid: COMID of the feature to search, defaults to None
    :type comid: str, optional
    :return: Set of features matching the search.
    :rtype: FeatureCollection
    """
    global NLDI_API
    NLDI_API.require_plugin("FlowlinePlugin")
    try:
        r = NLDI_API.plugins["FlowlinePlugin"].get_by_id(comid)
    except KeyError:
        LOGGER.info(f"COMID {comid} not found; returning 404")
        return flask.Response(status=http.HTTPStatus.NOT_FOUND)

    return flask.Response(
        headers={"Content-Type": "application/json"},
        status=http.HTTPStatus.OK,
        response=util.stream_j2_template("FeatureCollection.j2", [r]),
    )


# Much like the above, this route short-circuits the normal source lookup, a behavior specific to the 'comid' source.
@ROOT.route("/linked-data/comid/position")
def get_flowline_by_position():
    """
    Find flowline(s) by spatial search.

    :return: flowline features matching the spatial intersection.
    :rtype: FeatureCollection
    """
    global NLDI_API
    NLDI_API.require_plugin("FlowlinePlugin")
    NLDI_API.require_plugin("CatchmentPlugin")

    if (coords := flask.request.args.get("coords")) is None:
        LOGGER.error("No coordinates provided")
        return flask.Response(status=http.HTTPStatus.BAD_REQUEST, response="No coordinates provided")

    ## pre-checks all sorted... let's look for some stuff:
    try:
        ## Get the COMID for the provided coordinates, taken to be the
        # nhdplus/catchmentsp polygon intersecting the supplied point
        comid = NLDI_API.plugins["CatchmentPlugin"].get_by_coords(coords)
    except KeyError:
        LOGGER.info(f"Unable to find COMID for coordinates {coords}; returning 404")
        return flask.Response(status=http.HTTPStatus.NOT_FOUND)

    ## TODO:  both lookups in the same try/except block?  keeping them separate lets us give
    # more specific error messages....   TBD.
    try:
        flowline_feature = NLDI_API.plugins["FlowlinePlugin"].get_by_id(comid)
    except KeyError:
        LOGGER.info(f"COMID {comid} not found using FlowLine; returning 404")
        return flask.Response(status=http.HTTPStatus.NOT_FOUND)

    ## Formatting the response
    content = util.stream_j2_template("FeatureCollection.j2", [flowline_feature])
    return flask.Response(
        headers={"Content-Type": "application/json"},
        status=http.HTTPStatus.OK,
        response=content,
    )


@ROOT.route("/linked-data/hydrolocation")
def hydrolocation():
    """
    Find hydrolocation for a given set of coordinates.

    :return: Hydrolocation selected by spatial intersection with coordinates.
    :rtype: FeatureCollection
    """
    global NLDI_API
    NLDI_API.require_plugin("CatchmentPlugin")
    NLDI_API.require_plugin("HydroLocationPlugin")

    if (coords := flask.request.args.get("coords")) is None:
        LOGGER.error("No coordinates provided")
        return flask.Response(status=http.HTTPStatus.BAD_REQUEST, response="No coordinates provided")
    try:
        _hydro_location = NLDI_API.plugins["HydroLocationPlugin"].get_by_coords(coords)
    except Exception as e:
        LOGGER.error(f"Error getting hydrolocation for coordinates {coords}: {e}")
        return flask.Response(status=http.HTTPStatus.INTERNAL_SERVER_ERROR, response=str(e))
    return flask.jsonify(_hydro_location)


# region Routes Per-Source


@ROOT.route("/linked-data/<path:source_name>")
@ROOT.route("/linked-data/<path:source_name>/<path:identifier>")
def get_source_features(source_name=None, identifier=None) -> List[Dict[str, Any]]:
    """
    Return one or more features from a given source.

    This endpoint supports a "list mode" if no identifier given, returning all features from the source. If
    an identifier is given, only that feature is returned (assuming it is found in the table).  In the case
    where an identifier is provided but not found, a 404 is returned.

    :param source_name: the suffix for the source to search, defaults to None
    :type source_name: str, optional
    :param identifier: The source-specific unique identifier for the feature to find, defaults to None
    :type identifier: str, optional
    :return: A GeoJSON FeatureCollection of the feature(s) found.
    :rtype: List[Dict[str, Any]]
    """
    global NLDI_API
    NLDI_API.require_plugin("FeaturePlugin")
    if identifier:
        try:
            feature = NLDI_API.plugins["FeaturePlugin"].get_by_id(identifier, source_name)
            features = [feature]
        except KeyError as e:
            # Either the source or the identifier doesn't exist.
            _r = flask.jsonify(type="error", description=str(e))
            _r.status = http.HTTPStatus.NOT_FOUND
            return _r
    else:  # No identifier given; return all features from this source
        try:
            features = NLDI_API.plugins["FeaturePlugin"].get_all(source_name)
        except KeyError as e:
            LOGGER.info("No Such Source: {source_name}")
            # KeyError indicates that the source doesn't exist.
            _r = flask.jsonify(type="error", description=str(e))
            _r.status = http.HTTPStatus.NOT_FOUND
            return _r

    return flask.Response(
        headers={"Content-Type": "application/json"},
        status=http.HTTPStatus.OK,
        response=util.stream_j2_template("FeatureCollection.j2", features),
    )


@ROOT.route("/linked-data/<path:source_name>/<path:identifier>/basin")
def get_basin(source_name=None, identifier=None):
    """
    Locate the basin matching the named source and feature.

    :param source_name: source identifier, defaults to None
    :type source_name: str, optional
    :param identifier: feature identifier, defaults to None
    :type identifier: str, optional
    :return: Features matching the basins associated with the named feature/source.
    :rtype: FeatureCollection
    """
    global NLDI_API
    simplified = flask.request.args.get("simplified", "true").lower() == "true"
    split = flask.request.args.get("split", "false").lower() == "true"
    NLDI_API.require_plugin("BasinPlugin")
    try:
        features = NLDI_API.plugins["BasinPlugin"].get_by_id(
            identifier, source_name, simplified=simplified, split=split
        )
    except KeyError as e:
        return flask.Response(status=http.HTTPStatus.NOT_FOUND, response=str(e))
    content = util.stream_j2_template("FeatureCollection.j2", features)
    return flask.Response(
        headers={"Content-Type": "application/json"},
        status=http.HTTPStatus.OK,
        response=content,
    )


@ROOT.route("/linked-data/<path:source_name>/<path:identifier>/navigation")  # << NOTE: no nav_mode here.
def get_navigation_modes(source_name: str | None = None, identifier: str | None = None):
    """
    Identify the endpoints for each of the navigation modes possible from this source and feature.

    :param source_name: source identifier, defaults to None
    :type source_name: str | None, optional
    :param identifier: feature identifier, defaults to None
    :type identifier: str | None, optional
    :return: List of navigation modes
    :rtype: List[Dict[str, Any]]
    """
    global NLDI_API

    source_name = source_name.lower()

    # verify that the source exists:
    try:
        _ = NLDI_API.sources.get_by_id(source_name)
    except KeyError:
        return flask.Response(status=http.HTTPStatus.NOT_FOUND, response="Source not found: {source_name}")

    nav_url = util.url_join(NLDI_API.base_url, "linked-data", source_name, identifier, "navigation")
    content = {
        "upstreamMain": util.url_join(nav_url, "UM"),
        "upstreamTributaries": util.url_join(nav_url, "UT"),
        "downstreamMain": util.url_join(nav_url, "DM"),
        "downstreamDiversions": util.url_join(nav_url, "DD"),
    }
    return flask.jsonify(content)


@ROOT.route("/linked-data/<path:source_name>/<path:identifier>/navigation/<path:nav_mode>")
def get_navigation_info(source_name: str | None = None, identifier: str | None = None, nav_mode: str | None = None):
    """
    Fetch navigation information for a named source and feature.

    :param source_name: Source identifier, defaults to None
    :type source_name: str | None, optional
    :param identifier: feature identifier, defaults to None
    :type identifier: str | None, optional
    :param nav_mode: Navigation mode, defaults to None
    :type nav_mode: str | None, optional
    :return: set of navigation options for this feature/source
    :rtype: dict
    """
    source_name = source_name.lower()

    # verify that the source exists:
    try:
        _ = NLDI_API.sources.get_by_id(source_name)
    except KeyError:
        return flask.Response(status=http.HTTPStatus.NOT_FOUND, response="Source not found: {source_name}")

    nav_url = util.url_join(NLDI_API.base_url, "linked-data", source_name, identifier, "navigation")

    content = [
        {
            "source": "Flowlines",
            "sourceName": "NHDPlus flowlines",
            "features": util.url_join(nav_url, nav_mode, "flowlines"),
        }
    ]
    for source in NLDI_API.sources.get_all():
        src_id = source["source_suffix"]
        content.append(
            {
                "source": src_id,
                "sourceName": source["source_name"],
                "features": util.url_join(nav_url, nav_mode, src_id.lower()),
            }
        )
    return flask.jsonify(content)


@ROOT.route("/linked-data/<path:source_name>/<path:identifier>/navigation/<path:nav_mode>/flowlines")
def get_flowline_navigation(source_name=None, identifier=None, nav_mode=None):
    """
    Navigation along flowlines.

    :param source_name: source identifier, defaults to None
    :type source_name: str, optional
    :param identifier: unique feature identifier, defaults to None
    :type identifier: str, optional
    :param nav_mode: Navigation mode, defaults to None
    :type nav_mode: str, optional
    :return: Flowline features matching the nav walk.
    :rtype: FeatureCollection
    """
    global NLDI_API
    NLDI_API.require_plugin("FeaturePlugin")
    NLDI_API.require_plugin("FlowlinePlugin")

    source_name = source_name.lower()
    try:
        _d = flask.request.args["distance"]
        distance = float(_d)
    except KeyError as e:
        return flask.Response(status=http.HTTPStatus.BAD_REQUEST, response="No distance provided")
    except (TypeError, ValueError) as e:
        return flask.Response(status=http.HTTPStatus.BAD_REQUEST, response="Invalid distance provided")

    trim_start = False
    try:
        _t = flask.request.args["trimStart"]
        trim_start = _t.lower() == "true"
    except KeyError as e:
        trim_start = False
    except (TypeError, ValueError) as e:
        return flask.Response(status=http.HTTPStatus.BAD_REQUEST, response="Invalid trimStart provided")

    try:
        if source_name == "comid":
            _id = NLDI_API.plugins["FlowlinePlugin"].get_by_id(identifier)
            start_comid = int(_id)
        else:
            feature = NLDI_API.plugins["FeaturePlugin"].get_by_id(
                identifier, source_name
            )  # <<< ATTENTION: ``feature`` is instantiated here.
            start_comid = int(feature["properties"]["comid"])
    except (KeyError, ValueError):
        return flask.Response(
            status=http.HTTPStatus.INTERNAL_SERVER_ERROR,
            response=f"Error getting COMID for {identifier=}, {source_name=}",
        )

    LOGGER.info(f"Attempting {nav_mode} navigation for {distance=}, with {trim_start=}")
    nav_results = build_nav_query(nav_mode, start_comid, distance)
    LOGGER.info(f"Navigation query: {nav_results}")

    if trim_start is True:
        if source_name == "comid":  ##<< this should never happen for trimmed navigation.
            return flask.Response(
                status=http.HTTPStatus.BAD_REQUEST, response="Cannot trim navigation from COMID source."
            )
        ## ATTENTION: ``feature`` must be instantiated before this point.
        try:
            trim_tolerance = float(request.params.get("trimTolerance", 0.0))
        except ValueError:
            msg = "Request parameter 'trimTolerance' must be a number."
            return flask.Response(status=http.HTTPStatus.BAD_REQUEST, response=msg)

        LOGGER.debug(f"Trimming flowline with {trim_tolerance=}")
        try:
            measure = feature["properties"]["measure"]
            if not measure:  # only happens if measure is supplied as zero
                measure = estimate_measure(identifier, source_name)
            measure = float(measure)
            LOGGER.debug(f"Trim navigation: {measure=}")
        except KeyError:
            msg = "Required field 'measure' is not present."
            return flask.Response(status=http.HTTPStatus.BAD_REQUEST, response=msg)
        except ValueError:
            msg = "Required field 'measure' must be a number."
            return flask.Response(status=http.HTTPStatus.BAD_REQUEST, response=msg)

        trim_nav = trim_nav_query(nav_mode, start_comid, trim_tolerance, measure)
        features = NLDI.plugins["FlowlinePlugin"].trim_navigation(nav, trim_nav)
    else:
        features = NLDI_API.plugins["FlowlinePlugin"].lookup_navigation(nav_results)

    content = util.stream_j2_template("FeatureCollection.j2", features)

    return flask.Response(
        headers={"Content-Type": "application/json"},
        status=http.HTTPStatus.OK,
        response=content,
    )


@ROOT.route("/linked-data/<path:source_name>/<path:identifier>/navigation/<path:nav_mode>/<path:data_source>")
def get_navigation(source_name=None, identifier=None, nav_mode=None, data_source=None):
    """
    Navigates the feature topology according to navigation mode.

    Returns a GeoJSON feature collection representing the features included in the nav walk.

    :param source_name: Identifier for data source, defaults to None
    :type source_name: str, optional
    :param identifier: feature unique identifier, defaults to None
    :type identifier: str, optional
    :param nav_mode: Navigation Mode, defaults to None
    :type nav_mode: str, optional
    :param data_source: secondary data source, defaults to None
    :type data_source: str, optional
    :return: Features included in the navigation walk.
    :rtype: FeatureCollection
    """
    global NLDI_API
    NLDI_API.require_plugin("FeaturePlugin")
    NLDI_API.require_plugin("FlowlinePlugin")

    def _get_start_comid(identifier: str, source_name: str) -> int:
        global NLDI_API
        if source_name == "comid":
            _id = NLDI_API.plugins["FlowlinePlugin"].get_by_id(identifier)
            return int(_id)
        else:
            feature = NLDI_API.plugins["FeaturePlugin"].get_by_id(identifier, source_name)
            return int(feature["properties"]["comid"])

    source1_name = source_name.lower()
    source2_name = data_source.lower()

    try:
        _d = flask.request.args["distance"]
        distance = float(_d)
    except KeyError as e:
        return flask.Response(status=http.HTTPStatus.BAD_REQUEST, response="No distance provided")
    except (TypeError, ValueError) as e:
        return flask.Response(status=http.HTTPStatus.BAD_REQUEST, response="Invalid distance provided")

    try:
        start_comid = _get_start_comid(identifier, source1_name)
    except (KeyError, ValueError) as e:
        return flask.Response(
            status=http.HTTPStatus.INTERNAL_SERVER_ERROR,
            response=f"Error getting COMID for {identifier=}: {str(e)}",
        )

    try:
        nav_results = build_nav_query(nav_mode, start_comid, distance)
    except ValueError as e:
        return flask.Response(status=http.HTTPStatus.BAD_REQUEST, response=str(e))

    try:
        source2_info = NLDI_API.sources.get_by_id(source2_name)
        LOGGER.info(f"source2_info: {source2_info}")
    except KeyError as e:
        _r = flask.jsonify(description=str(e), type="error")
        _r.status = http.HTTPStatus.NOT_FOUND
        return _r

    features = NLDI_API.plugins["FeaturePlugin"].lookup_navigation(nav_results, source2_info)

    return flask.Response(
        headers={"Content-Type": "application/json"},
        status=http.HTTPStatus.OK,
        response=util.stream_j2_template("FeatureCollection.j2", features),
    )


# region APP Creation
def app_factory(api: API) -> flask.Flask:
    """
    Create the Flask app with the given API instance.

    We're choosing to make the main Flask APP using a factory function to give the possibility
    that the app can be created with different API configurations. This mostly a concession
    to testability -- mocked and faked APIs can be used to test APP functionality more easily
    with this setup.
    """
    global NLDI_API
    global ROOT

    app = flask.Flask(__name__)
    if app is None:
        raise RuntimeError("NLDI API Server >> Failed to initialize Flask app")
    NLDI_API = api

    app.url_map.strict_slashes = False
    CORS(app)
    app.register_blueprint(ROOT, url_prefix="/api/nldi")

    ## This is the app we'll be serving...
    return app


# region APP
APP = app_factory(API(globalconfig=CONFIG))
## ^^^^^^^^  this is the standard startup, where APP is the thing we care about.
## But for testing or special cases, you can send a different API in (with a different
## ``globalconfig``) to make a custom app.
