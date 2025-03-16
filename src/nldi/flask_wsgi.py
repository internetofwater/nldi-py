#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""Flask Endpoints and Routes"""

import flask
from flask_cors import CORS

from .config import get_config
from .server.flask_routers import ROOT


def flask_nldi_app_factory() -> flask.Flask:
    _cfg = get_config()

    app = flask.Flask(__name__)
    if not app:
        raise RuntimeError("NLDI API SERVER >> Failed to initialize Flask app")
    app.url_map.strict_slashes = False
    CORS(app)
    app.register_blueprint(ROOT, url_prefix=_cfg.server.prefix)
    app.NLDI_CONFIG = _cfg
    return app


APP = flask_nldi_app_factory()
