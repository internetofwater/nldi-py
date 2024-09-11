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

from . import LOGGER, __version__, log, util
from .config import Configuration
from .api.main import API


def update_headers(r: flask.Response) -> flask.Response:
    """
    Create a Flask Response object and update matching headers.
    :param result: The result of the API call.
                   This should be a tuple of (headers, status, content).
    :returns: A Response instance.
    """  # noqa: D205
    ## The following is a dictionary of headers that will be added to all responses:
    _RESPONSE_HEADERS = {  # noqa: N806
        "X-Powered-By": f"nldi {__version__}"
    }
    r.headers.update(_RESPONSE_HEADERS)
    return r


# region:: Main Flask App
APP = flask.Flask(__name__)
if APP is None:
    raise RuntimeError("NLDI API Server >> Failed to initialize Flask app")

log.initialize(LOGGER, level="DEBUG")
##TODO: The log level  should be a configurable option, perhaps set with -V or --verbose switch.

## Loading CONFIG here, after loggers and whatnot are set up.
CONFIG = Configuration(os.environ.get("NLDI_CONFIG"))

LOGGER.info(f"NLDI v{__version__} API Server >> Starting Up")
log.versions(logger=LOGGER)
APP.url_map.strict_slashes = False
CORS(APP)
NLDI_API = API(globalconfig=CONFIG)


ROOT = flask.Blueprint("nldi", __name__)


@ROOT.route("/")
def home() -> flask.Response:
    LOGGER.debug(f"{flask.request.method} {flask.request.url}")
    content = {
        "title": CONFIG["metadata"]["identification"]["title"],
        "description": CONFIG["metadata"]["identification"]["description"],
        "links": [
            {
                "rel": "data",
                "type": "application/json",
                "title": "Sources",
                "href": f"{CONFIG['base_url']}linked-data",
            },
            {
                "rel": "service-desc",
                "type": "text/html",
                "title": "The OpenAPI definition as HTML",
                "href": f"{CONFIG['base_url']}openapi?f=html",
            },
            {
                "rel": "service-desc",
                "type": "application/vnd.oai.openapi+json;version=3.0",
                "title": "The OpenAPI definition as JSON",
                "href": f"{CONFIG['base_url']}openapi?f=json",
            },
        ],
    }
    return update_headers(flask.jsonify(content))


@ROOT.route("/favicon.ico")
def favicon():
    LOGGER.debug(f"{flask.request.method} {flask.request.url}")
    return flask.send_from_directory("./static/", "favicon.ico", mimetype="image/vnd.microsoft.icon")


@ROOT.route("/openapi")
def openapi_spec() -> Tuple[dict, int, str]:
    """
    Return the OpenAPI document spec using either the swagger or redoc UI.

    :param request: Incoming API request
    :type request: _type_
    """
    global CONFIG
    LOGGER.debug(f"{flask.request.method} {flask.request.url}")

    if requested_format := flask.request.args.get("f", "html") == "html":
        if flask.request.args.get("ui") == "redoc":
            template = "openapi/redoc.html"
        else:
            template = "openapi/swagger.html"
        data = {"openapi-document-path": f"/openapi"}  ##TODO:  Move away from hard-coded path.

        content = render_j2_template(CONFIG, template, data)
        return update_headers(
            flask.Response(headers={"Content-Type": "text/html"}, status=http.HTTPStatus.OK, response=content)
        )
    else:
        r = flask.jsonify(NLDI_API.openapi_json)
        r.headers["Content-Type"] = "application/vnd.oai.openapi+json;version=3.0"  # noqa
        return update_headers(r)


@ROOT.route("/linked-data")
def sources() -> flask.Response:
    """
    Linked Data Sources endpoint

    :returns: HTTP response
    """
    LOGGER.debug(f"{flask.request.method} {flask.request.url}")

    content = [
        {
            "source": "comid",
            "sourceName": "NHDPlus comid",
            "features": util.url_join(CONFIG["base_url"], "linked-data/comid/position"),
        }
    ]
    for s in NLDI_API.sources.get_all():
        content.append(
            {
                "source": s["source_suffix"],
                "sourceName": s["source_name"],
                "features": util.url_join(
                    CONFIG["base_url"], f"linked-data/{s["source_suffix"].lower()}", allow_fragments=True
                ),
            }
        )
    return update_headers(flask.jsonify(content))

@ROOT.route("/linked-data/hydrolocation")
def hydrolocation():
    return update_headers(API_.get_hydrolocation(request))


@ROOT.route("/linked-data/comid/<int:comid>")
def get_flowline_by_comid(comid=None):
    LOGGER.debug(f"{flask.request.method} {flask.request.url}")
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
    return update_headers(flask.jsonify(r))

@ROOT.route("/linked-data/comid/position")
def get_flowline_by_position():
    LOGGER.debug(f"{flask.request.method} {flask.request.url}")
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
            LOGGER.error("Failed to register FlowlinePlugin")
            raise RuntimeError("Failed to register FlowlinePlugin")
    try:
        coords = flask.request.params["coords"]
    except KeyError:
        LOGGER.error("No coordinates provided")
        return flask.Response(status=http.HTTPStatus.BAD_REQUEST, response="No coordinates provided")

    try:
        r = NLDI_API.plugins["FlowLine"].get(comid)
        comid = NLDI_API.plugins["Catchment"].get_by_coords(coords)
    except KeyError:
        LOGGER.info(f"Unable to find COMID for coordinates {coords}; returning 404")
        return flask.Response(status=http.HTTPStatus.NOT_FOUND)

    return update_headers(flask.jsonify(r))

APP.register_blueprint(ROOT)
