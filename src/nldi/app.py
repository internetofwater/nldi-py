#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

"""API entry point for NLDI services"""

from typing import Dict

import click
import flask
from flask_cors import CORS

from . import LOGGER

STATIC_FOLDER = "static"


APP = flask.Flask(__name__, static_folder=STATIC_FOLDER, static_url_path=f"/{STATIC_FOLDER}")
APP.url_map.strict_slashes = False
CORS(APP)

BLUEPRINT = flask.Blueprint("nldi", __name__, static_folder=STATIC_FOLDER)


@BLUEPRINT.route("/admin/ping")
def ping() -> Dict[str, str]:
    """Health check endpoint"""
    return {"PING": "ACK"}


APP.register_blueprint(BLUEPRINT, url_prefix="/api/nldi")
