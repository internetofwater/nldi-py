#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
""" """

import http
import logging
from copy import deepcopy
from typing import Any, Literal, TypeVar

import flask
import msgspec
from sqlalchemy.ext.asyncio import AsyncSession

from .. import __version__, util
from ..config import MasterConfig, status
from ..domain.linked_data import services

ROOT = flask.Blueprint("nldi", __name__)


@ROOT.before_request
def log_incoming_request() -> None:
    """Implement simple middleware function to log requests."""
    logging.debug(f"{flask.request.method} {flask.request.url}")
    # TODO: other pre-request activities can go here.

    rp = flask.request.path
    if rp != "/" and rp.endswith("/"):
        return flask.redirect(rp[:-1])

    ## Sets up a callback to update headers after the request is processed.
    @flask.after_this_request
    def update_headers(r: flask.Response) -> flask.Response:
        """Implement simple middlware function to update response headers."""
        r.headers.update(
            {
                "X-Powered-By": f"nldi {__version__} and FLASK",
            }
            # TODO: add headers to this dict that you want in every response.
        )
        return r


@ROOT.route("/")
def home():
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
@ROOT.route("/about")
def app_info() -> dict[str, Any]:
    _ = flask.request
    return {
        "name": "nldi-py",
        "version": __version__,
    }


@ROOT.route("/about/config")
def app_configuration():
    _app = flask.current_app
    _sanitized_config = deepcopy(_app.NLDI_CONFIG)
    _sanitized_config.db.password = "***"  # noqa: S105
    return {
        "server": vars(_sanitized_config.server),
        "db": vars(_sanitized_config.db),
        "metadata": vars(_sanitized_config.metadata),
    }


@ROOT.route("/about/health")
def healthcheck():
    """Simple healthcheck for app and its dependent services."""
    _cfg = flask.current_app.NLDI_CONFIG
    return {
        "server": msgspec.structs.asdict(_cfg.server.healthstatus()),
        "db": msgspec.structs.asdict(_cfg.db.healthstatus()),
        "pygeoapi": msgspec.structs.asdict(_cfg.server.healthstatus("pygeoapi")),
    }


# region  Linked-Data


@ROOT.route("/linked-data")
async def list_sources():
    db = flask.current_app.NLDI_CONFIG.db
    async with AsyncSession(bind=db.async_engine) as db_session:
        async with services.CrawlerSourceService.new(session=db_session) as sources_svc:
            src_list = await sources_svc.list()
            _r = list(src_list)
    return [f._as_dict for f in _r]


@ROOT.route("/linked-data/comid/<int:comid>")
async def get_flowline_by_comid(comid: int | None = None):
    db = flask.current_app.NLDI_CONFIG.db
    base_url = flask.current_app.NLDI_CONFIG.server.base_url

    async with AsyncSession(bind=db.async_engine) as db_session:
        async with services.FlowlineService.new(session=db_session) as flowline_svc:
            try:
                flowline_feature = await flowline_svc.get_feature(
                    comid,
                    xtra_props={"navigation": util.url_join(base_url, "comid", comid, "navigation")},
                )
            except NotFoundError:
                raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"COMID {comid} not found.")
        _r = flask.Response(
            headers={"Content-Type": "application/json"},
            status=http.HTTPStatus.OK,
            response=util.stream_j2_template("FeatureCollection.j2", [msgspec.structs.asdict(flowline_feature)]),
        )
    return _r


@ROOT.route("/linked-data/<path:source_name>/<path:identifier>")
async def get_feature_by_identifier(source_name: str, identifier: str):
    db = flask.current_app.NLDI_CONFIG.db
    base_url = flask.current_app.NLDI_CONFIG.server.base_url

    async with AsyncSession(bind=db.async_engine) as db_session:
        async with services.FeatureService.new(session=db_session) as feature_svc:
            feature = await feature_svc.feature_lookup(source_name, identifier)
            if not feature:
                raise HTTPException(status_code=HTTP_404_NOT_FOUND)
            nav_url = util.url_join(
                flask.current_app.NLDI_CONFIG.server.base_url, "linked-data", source_name, identifier, "navigation"
            )
            _geojson = feature.as_feature(excl_props=["crawler_source_id"], xtra_props={"navigation": nav_url})
            _r = flask.Response(
                headers={"Content-Type": "application/json"},
                status=http.HTTPStatus.OK,
                response=util.stream_j2_template("FeatureCollection.j2", [msgspec.structs.asdict(_geojson)]),
            )
    return _r

@ROOT.route("/linked-data/<path:source_name>/<path:identifier>/navigation")
def get_navigation_modes(source_name:str, identifier: str):
    db = flask.current_app.NLDI_CONFIG.db
    base_url = flask.current_app.NLDI_CONFIG.server.base_url
    async with AsyncSession(bind=db.async_engine) as db_session:
        async with services.CrawlerSourceService.new(session=db_session) as sources_svc:
            src_exists = await sources_svc.suffix_exists(source_name)
            if not src_exists:
                raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"No such source: {source_name}")

    nav_url = util.url_join(base_url, "linked-data", source_name, identifier, "navigation")
    content = {
        "upstreamMain": util.url_join(nav_url, "UM"),
        "upstreamTributaries": util.url_join(nav_url, "UT"),
        "downstreamMain": util.url_join(nav_url, "DM"),
        "downstreamDiversions": util.url_join(nav_url, "DD"),
    }
    return content
