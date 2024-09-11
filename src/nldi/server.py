#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

import http
import os
from typing import Dict, List, Tuple

import flask
from flask_cors import CORS
from pygeoapi.util import render_j2_template  ##TODO: can we drop this dependency? Need to figure out templating
from nldi.util import stream_j2_template
from . import LOGGER, __version__, log, util
from .config import Configuration
from .api.main import API


# region:: Main Flask App
APP = flask.Flask(__name__)
if APP is None:
    raise RuntimeError("NLDI API Server >> Failed to initialize Flask app")

@APP.before_request
def log_incoming_request() -> None:
    """Simple middleware function to log requests."""
    LOGGER.debug(f"{flask.request.method} {flask.request.url}")

    ## Sets up a callback to update headers after the request is processed.
    @flask.after_this_request
    def update_headers(r: flask.Response) -> flask.Response:
        """Simple middlware function to update response headers.    """
        r.headers.update({
            "X-Powered-By": f"nldi {__version__}",
        })
        return r

log.initialize(LOGGER, level="DEBUG")
##TODO: The log level  should be a configurable option, perhaps set with -V or --verbose switch.

## Loading CONFIG here, after loggers and whatnot are set up.
if "NLDI_CONFIG" not in os.environ:
    raise RuntimeError("NLDI_CONFIG environment variable not set")
CONFIG = Configuration(os.environ.get("NLDI_CONFIG"))

LOGGER.info(f"NLDI v{__version__} API Server >> Starting Up")
log.versions(logger=LOGGER)
APP.url_map.strict_slashes = False
CORS(APP)


NLDI_API = API(globalconfig=CONFIG)
ROOT = flask.Blueprint("nldi", __name__)


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
                "href": util.url_join(CONFIG['base_url'], "linked-data"),
            },
            {
                "rel": "service-desc",
                "type": "text/html",
                "title": "The OpenAPI definition as HTML",
                "href": util.url_join(CONFIG['base_url'] , "openapi?f=html"),
            },
            {
                "rel": "service-desc",
                "type": "application/vnd.oai.openapi+json;version=3.0",
                "title": "The OpenAPI definition as JSON",
                "href": util.url_join(CONFIG['base_url'], "openapi?f=json"),
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
    global CONFIG
    if requested_format := flask.request.args.get("f", "html") == "html":
        if flask.request.args.get("ui") == "redoc":
            template = "openapi/redoc.html"
        else:
            template = "openapi/swagger.html"
        data = {"openapi-document-path": f"openapi"} ##NOTE: intentionally using relative path here.

        content = render_j2_template(CONFIG, template, data)
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
    content = [
        {
            "source": "comid",
            "sourceName": "NHDPlus comid",
            "features": util.url_join(CONFIG["base_url"], "linked-data",  "comid",  "position"),
        }
    ] ## This source is hard-coded -- should always be available.  Other sources are loaded from the source table.
    for s in NLDI_API.sources.get_all():
        content.append(
            {
                "source": s["source_suffix"],
                "sourceName": s["source_name"],
                "features": util.url_join(CONFIG["base_url"], "linked-data", s["source_suffix"].lower()),
            }
        )
    return flask.jsonify(content)

@ROOT.route("/linked-data/hydrolocation")
def hydrolocation():
    return API_.get_hydrolocation(request)


@ROOT.route("/linked-data/comid/<int:comid>")
def get_flowline_by_comid(comid=None):
    if "FlowLine" not in NLDI_API.plugins:
        from .api import FlowlinePlugin  # noqa: I001
        if NLDI_API.register_plugin(FlowlinePlugin("FlowLine")):
            LOGGER.debug("Loaded FlowLine plugin")
        else:
            LOGGER.error("Failed to register FlowlinePlugin")
            raise RuntimeError("Failed to register FlowlinePlugin")
    try:
        r = NLDI_API.plugins["FlowLine"].get(comid)
    except KeyError:
        LOGGER.info(f"COMID {comid} not found; returning 404")
        return flask.Response(status=http.HTTPStatus.NOT_FOUND)
    return flask.jsonify(r)

@ROOT.route("/linked-data/comid/position")
def get_flowline_by_position():
    ## TODO:  Refactor all this plugin loading into a single function for re-use elsewhere.
    if "FlowLine" not in NLDI_API.plugins:
        from .api import FlowlinePlugin # noqa: I001
        if NLDI_API.register_plugin(FlowlinePlugin("FlowLine")):
            LOGGER.debug("Loaded FlowLine plugin")
        else:
            LOGGER.error("Failed to register FlowlinePlugin")
            raise RuntimeError("Failed to register FlowlinePlugin")

    if "Catchment" not in NLDI_API.plugins:
        from .api import CatchmentPlugin # noqa: I001
        if NLDI_API.register_plugin(CatchmentPlugin("Catchment")):
            LOGGER.debug("Loaded Catchment plugin")
        else:
            LOGGER.error("Failed to register CatchmentPlugin")
            raise RuntimeError("Failed to register CatchmentPlugin")

    if (coords := flask.request.args.get("coords")) is None:
        LOGGER.error("No coordinates provided")
        return flask.Response(status=http.HTTPStatus.BAD_REQUEST, response="No coordinates provided")

    try:
        comid = NLDI_API.plugins["Catchment"].get_by_coords(coords)
    except KeyError:
        LOGGER.info(f"Unable to find COMID for coordinates {coords}; returning 404")
        return flask.Response(status=http.HTTPStatus.NOT_FOUND)

    try:
        flowline_feature = NLDI_API.plugins["FlowLine"].get(comid)
    except KeyError:
        LOGGER.info(f"COMID {comid} not found; returning 404")
        return flask.Response(status=http.HTTPStatus.NOT_FOUND)


    content = stream_j2_template("FeatureCollection.j2", [flowline_feature])
    return flask.Response(
        headers={"Content-Type": "application/json"},
        status=http.HTTPStatus.OK,
        response=content,
    )

APP.register_blueprint(ROOT, url_prefix="/api/nldi")