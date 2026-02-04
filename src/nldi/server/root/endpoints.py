#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""Routers/blueprints for flask app endpoints."""

import http
import json
import logging
from copy import deepcopy
from typing import Any, Literal, TypeVar

import flask
import msgspec

from ... import __version__, util
from ...config import MasterConfig, status

ROOT = flask.Blueprint("nldi", __name__)


@ROOT.before_request
def root_incoming_request() -> None:
    rp = flask.request.path
    if rp != "/" and rp.endswith("/"):
        return flask.redirect(rp[:-1])
    logging.info(f"{flask.request.method} {flask.request.url}")

@ROOT.after_request
def root_post_request_actions(r: flask.Response) -> None:
    rp = flask.request.path
    logging.info(f"RETURN from {rp}")
    return r

@ROOT.route("/")
def home():
    """Landing Page"""
    _cfg = flask.current_app.NLDI_CONFIG
    return {
        "title": _cfg.metadata.title,
        "description": _cfg.metadata.description,
        "links": [
            {
                "rel": "data",
                "type": "application/json",
                "title": "Sources",
                "href": util.url_join(_cfg.server.base_url, "linked-data"),
            },
            {
                "rel": "service-desc",
                "type": "text/html",
                "title": "The OpenAPI definition as HTML",
                "href": util.url_join(_cfg.server.base_url, "docs"),
            },
            {
                "rel": "service-desc",
                "type": "application/vnd.oai.openapi+json;version=3.0",
                "title": "The OpenAPI definition as JSON",
                "href": util.url_join(_cfg.server.base_url, "docs", "openapi.json"),
            },
        ],
    }


# region ABOUT


@ROOT.route("/about/health")
def healthcheck():
    """Simple healthcheck for app and its dependent services."""
    _cfg = flask.current_app.NLDI_CONFIG
    return {
        "server": msgspec.structs.asdict(_cfg.server.healthstatus()),
        "db": msgspec.structs.asdict(_cfg.db.healthstatus()),
        "pygeoapi": msgspec.structs.asdict(_cfg.server.healthstatus("pygeoapi")),
    }


@ROOT.route("/docs/openapi.json")
def openapi_json():
    from ..openapi import generate_openapi_json

    r = flask.jsonify(generate_openapi_json())
    r.headers["Content-Type"] = "application/vnd.oai.openapi+json;version=3.0"  # noqa
    return r


@ROOT.route("/docs")
def openapi_ui():
    template = "swagger.html"
    data = {"openapi-document-path": "docs/openapi.json"}  ## NOTE: intentionally using relative path here
    content = util.render_j2_template(template, data)
    return flask.Response(
        headers={"Content-Type": "text/html"},
        status=http.HTTPStatus.OK,
        response=content,
    )


@ROOT.route("/openapi")
def openapi_redirect():
    return flask.redirect("docs")
