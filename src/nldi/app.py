#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

"""
API entry point for NLDI services.

This is the main entry point for the NLDI API, to be served
via a WSGI server such as Gunicorn or Uvicorn.

Typical launch command:

>>> guicorn nldi.app:APP --bind hostname:port

"""

from typing import Dict

import flask
from flask_cors import CORS

from . import LOGGER

STATIC_FOLDER = "static"  ## TODO: config info like this should probably be in a config file.


APP = flask.Flask(__name__, static_folder=STATIC_FOLDER, static_url_path=f"/{STATIC_FOLDER}")
APP.url_map.strict_slashes = False
CORS(APP)

BLUEPRINT = flask.Blueprint("nldi", __name__, static_folder=STATIC_FOLDER)


@BLUEPRINT.route("/admin/ping")
def ping() -> Dict[str, str]:
    """Health-check endpoint"""
    return {"PING": "ACK"}


@BLUEPRINT.route("/favicon.ico")
def favicon():
    return flask.send_from_directory(STATIC_FOLDER, "favicon.ico", mimetype="image/vnd.microsoft.icon")

APP.register_blueprint(BLUEPRINT, url_prefix="/api/nldi")
