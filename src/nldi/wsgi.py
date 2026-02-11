#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""Flask Endpoints and Routes"""

import logging
import os

import flask
from advanced_alchemy.config.engine import EngineConfig
from advanced_alchemy.extensions.flask import AdvancedAlchemy, SQLAlchemySyncConfig
from flask_cors import CORS
from sqlalchemy.exc import OperationalError

from .config import get_config, log_level
from .server.linked_data.endpoints import LINKED_DATA
from .server.root.endpoints import ROOT


def flask_nldi_app_factory() -> flask.Flask:
    _cfg = get_config()
    logging.basicConfig(level=logging.DEBUG)  ## Debug for startup... will set to a more modest level later.

    app = flask.Flask(__name__)
    if not app:
        raise RuntimeError("NLDI API SERVER >> Failed to initialize Flask app")
    app.url_map.strict_slashes = False
    CORS(app)
    app.register_blueprint(ROOT, url_prefix=_cfg.server.prefix)
    app.register_blueprint(LINKED_DATA, url_prefix=f"{_cfg.server.prefix}/linked-data")
    logging.info(f"Connection string: {_cfg.db.URL}")
    _alchemy_config = SQLAlchemySyncConfig(
        connection_string=_cfg.db.URL,
        create_all=False,
        engine_config=EngineConfig(
            pool_size=100,
            pool_recycle=60,
            pool_pre_ping=True,
            max_overflow=20,
            pool_timeout=30,
        ),
    )
    app.alchemy = AdvancedAlchemy(_alchemy_config, app)
    app.NLDI_CONFIG = _cfg
    logging.getLogger().setLevel(log_level())
    return app


APP = flask_nldi_app_factory()
