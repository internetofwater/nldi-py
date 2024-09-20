#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

import http
import os
from typing import Any, Dict, List, Tuple

import flask
from flask_cors import CORS
from pygeoapi.util import render_j2_template  ##TODO: can we drop this dependency? Need to figure out templating

from . import LOGGER, __version__, log, util
from .api.main import API
from .config import Configuration

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

        content = render_j2_template(NLDI_API.config, template, data)
        return flask.Response(
            headers={"Content-Type": "text/html"},
            status=http.HTTPStatus.OK,
            response=content,
        )
    else:
        r = flask.jsonify(NLDI_API.openapi_json)
        r.headers["Content-Type"] = "application/vnd.oai.openapi+json;version=3.0"  # noqa
        return r


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


@ROOT.route("/linked-data/comid/<int:comid>")
def get_flowline_by_comid(comid=None):
    global NLDI_API
    NLDI_API.require_plugin("FlowlinePlugin")
    try:
        r = NLDI_API.plugins["FlowlinePlugin"].get_by_id(comid)
    except KeyError:
        LOGGER.info(f"COMID {comid} not found; returning 404")
        return flask.Response(status=http.HTTPStatus.NOT_FOUND)
    return flask.jsonify(r)


@ROOT.route("/linked-data/comid/position")
def get_flowline_by_position():
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
    global NLDI_API
    NLDI_API.require_plugin("CatchmentPlugin") #< hydrolocation plugin requires catchment plugin internally.
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


@ROOT.route("/linked-data/<path:source_name>/<path:identifier>/basin")
def get_basin(source_name=None, identifier=None):
    r = flask.jsonify(
        {
            "message": "Not Implemented",
            "params": {"source_name": source_name, "identifier": identifier},
        }
    )
    return r  # return get_response(API_.get_basin(request, source_name, identifier))


@ROOT.route("/linked-data/<path:source_name>/<path:identifier>/navigation")  # noqa
@ROOT.route("/linked-data/<path:source_name>/<path:identifier>/navigation/<path:nav_mode>")  # noqa
def get_navigation_info(source_name=None, identifier=None, nav_mode=None):
    r = flask.jsonify(
        {
            "message": "Not Implemented",
            "params": {"source_name": source_name, "identifier": identifier, "nav_mode": nav_mode},
        }
    )
    return r  #     return get_response(API_.get_navigation_info(request, source_name, identifier, nav_mode))


@ROOT.route("/linked-data/<path:source_name>/<path:identifier>/navigation/<path:nav_mode>/flowlines")  # noqa
def get_flowline_navigation(source_name=None, identifier=None, nav_mode=None):  # noqa
    r = flask.jsonify(
        {
            "message": "Not Implemented",
            "params": {"source_name": source_name, "identifier": identifier},
        }
    )
    return r  # return get_response(API_.get_flowlines(request, source_name, identifier, nav_mode))


@ROOT.route("/linked-data/<path:source_name>/<path:identifier>/navigation/<path:nav_mode>/<path:data_source>")  # noqa
def get_navigation(source_name=None, identifier=None, nav_mode=None, data_source=None):  # noqa
    r = flask.jsonify(
        {
            "message": "Not Implemented",
            "params": {
                "source_name": source_name,
                "identifier": identifier,
                "nav_mode": nav_mode,
                "data_source": data_source,
            },
        }
    )
    return r


#     return get_response(API_.get_navigation(request, source_name, identifier, nav_mode, data_source))


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
    NLDI_API.require_plugin("FeaturePlugin")
    if identifier:
        try:
            feature = NLDI_API.plugins["FeaturePlugin"].get_by_id(identifier, source_name)
            features = [feature]
        except KeyError as e:
            # Either the source or the identifier doesn't exist.
            return flask.Response(status=http.HTTPStatus.NOT_FOUND, response=str(e))
    else:  # No identifier given; return all features from this source
        try:
            features = NLDI_API.plugins["FeaturePlugin"].get_all(source_name)
        except KeyError as e:
            # KeyError indicates that the source doesn't exist.
            return flask.Response(status=http.HTTPStatus.NOT_FOUND, response=str(e))

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
## ``globalconfig``).
