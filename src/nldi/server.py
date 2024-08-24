#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

import http

import flask
from flask_cors import CORS
from jinja2.environment import TemplateStream

from . import LOGGER, __version__, log, util


def update_headers(r: flask.Response) -> flask.Response:
    """
    Create a Flask Response object and update matching headers.
    :param result: The result of the API call.
                   This should be a tuple of (headers, status, content).
    :returns: A Response instance.
    """  # noqa: D205
    ## The following is a dictionary of headers that will be added to all responses:
    _RESPONSE_HEADERS = {  # noqa: N806
        "force_type": "application/json",
        "X-Powered-By": f"nldi {__version__}"
    }
    r.headers.update(_RESPONSE_HEADERS)
    return r


APP = flask.Flask(__name__)
if APP is None:
    raise RuntimeError("NLDI API Server >> Failed to initialize Flask app")

log.initialize(LOGGER, level="DEBUG") ##TODO: This should be a configurable option, set in the config file
LOGGER.info(f"NLDI v{__version__} API Server >> Starting Up")
log.versions(logger=LOGGER)

APP.url_map.strict_slashes = False
CORS(APP)

ROOT = flask.Blueprint("nldi", __name__)

@ROOT.route("/")
def home() -> flask.Response:
    LOGGER.debug(f"{flask.request.method} {flask.request.url}")
    content = {
        "title": "Sample Flask App",
        "description": "Functional test",
        "route_rule": flask.request.method,
    }
    return update_headers(flask.jsonify(content))


@ROOT.route("/favicon.ico")
def favicon():
    LOGGER.debug(f"{flask.request.method} {flask.request.url}")
    return flask.send_from_directory("./static/", "favicon.ico", mimetype="image/vnd.microsoft.icon")


APP.register_blueprint(ROOT)
