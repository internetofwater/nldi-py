#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
""" """

import http
import json
import logging
from copy import deepcopy
from typing import Any, Literal, TypeVar

import flask
import msgspec
from advanced_alchemy.exceptions import NotFoundError
from sqlalchemy.ext.asyncio import AsyncSession
from werkzeug.exceptions import BadRequest, NotFound, NotImplemented, ServiceUnavailable, UnprocessableEntity

from .. import __version__, util
from ..config import MasterConfig, status
from ..db.schemas import struct_geojson
from ..domain.linked_data import services

ROOT = flask.Blueprint("nldi", __name__)
LINKED_DATA = flask.Blueprint("linked-data", __name__)


@ROOT.before_request
def root_incoming_request() -> None:
    logging.debug(f"{flask.request.method} {flask.request.url}")

    rp = flask.request.path
    if rp != "/" and rp.endswith("/"):
        return flask.redirect(rp[:-1])


## Sets up a callback to update headers after the request is processed.
@ROOT.after_request
def update_headers(r: flask.Response) -> flask.Response:
    """Implement simple middlware function to update response headers."""
    r.headers.update({"X-Powered-By": f"nldi {__version__} and FLASK"})
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


@ROOT.route("/docs/openapi.json")
def openapi_json():
    from .openapi import generate_openapi_json

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


# region  Linked-Data
class HTML_JSON_Exception(Exception):
    pass


@LINKED_DATA.errorhandler(HTML_JSON_Exception)
def html_to_json_redirect(e) -> flask.Response:
    logging.debug("Redirection HTML")
    return flask.Response(
        response=f"""
                <html>
                An HTML representation is not available for this resource.
                <br/>
                If you would like to see the data as JSON, <a href="{e}">click here</a>.
                </html>
        """
    )


@LINKED_DATA.before_request
def parse_incoming_request() -> None:
    rp = flask.request.path
    if rp != "/" and rp.endswith("/"):
        return flask.redirect(rp[:-1])

    if flask.request.args.get("f") == "json":
        logging.debug(f"JSON specifically requested")
        return
    # NOTE: This is a special request for the interface:  If the requesting client accepts HTML, we
    # are assuming that it is a web browser or other general-purpose client. We want them to specifically
    # ask for JSON with the `f=json` query param.
    if flask.request.args.get("f") == "html" or flask.request.accept_mimetypes.accept_html:
        _q = dict(flask.request.args)
        _q["f"] = "json"
        _qstring = "&".join([f"{k}={v}" for k, v in _q.items()])
        logging.debug(f"REDIRECT from HTML")
        new_url = f"{rp}?{_qstring}"
        raise HTML_JSON_Exception(new_url)

    ## Sets up a callback to update headers after the request is processed.


@LINKED_DATA.after_request
def ld_update_headers(r: flask.Response) -> flask.Response:
    """Implement simple middlware function to update response headers."""
    r.headers.update({"X-Powered-By": f"nldi {__version__} and FLASK"})
    return r


@LINKED_DATA.route("/")
async def list_sources():
    db = flask.current_app.NLDI_CONFIG.db
    async with AsyncSession(bind=db.async_engine) as db_session:
        async with services.CrawlerSourceService.new(session=db_session) as sources_svc:
            src_list = await sources_svc.list()
            _r = list(src_list)
    return [f._as_dict for f in _r]


@LINKED_DATA.route("/hydrolocation")
async def get_hydrolocation():
    if (coords := flask.request.args.get("coords")) is None:
        return flask.Response(status=http.HTTPStatus.BAD_REQUEST, response="No coordinates provided")
    db = flask.current_app.NLDI_CONFIG.db
    base_url = flask.current_app.NLDI_CONFIG.server.base_url

    async with AsyncSession(bind=db.async_engine) as db_session:
        async with services.PyGeoAPIService.new(session=db_session) as pygeoapi_svc:
            try:
                features = await pygeoapi_svc.hydrolocation_by_coords(coords, base_url=base_url)
            except RuntimeError as e:
                raise ServiceUnavailable(description=str(e))
            except KeyError as e:
                raise NotFound(description=str(e))
    _r = flask.Response(
        headers={"Content-Type": "application/json"},
        status=http.HTTPStatus.OK,
        response=util.stream_j2_template("FeatureCollection.j2", [msgspec.structs.asdict(f) for f in features]),
    )
    return _r


@LINKED_DATA.route("/comid/<path:comid>")
async def get_flowline_by_comid(comid: int | None = None):
    db = flask.current_app.NLDI_CONFIG.db
    base_url = flask.current_app.NLDI_CONFIG.server.base_url
    try:
        _comid = int(comid)
    except Exception as e:
        raise BadRequest(f"Could not make {comid} an integer") from None

    async with AsyncSession(bind=db.async_engine) as db_session:
        async with services.FlowlineService.new(session=db_session) as flowline_svc:
            try:
                flowline_feature = await flowline_svc.get_feature(
                    comid,
                    xtra_props={"navigation": util.url_join(base_url, "comid", comid, "navigation")},
                )
            except NotFoundError:
                raise NotFound(description=f"COMID {comid} not found.")
        _r = flask.Response(
            headers={"Content-Type": "application/json"},
            status=http.HTTPStatus.OK,
            response=util.stream_j2_template("FeatureCollection.j2", [msgspec.structs.asdict(flowline_feature)]),
        )
    return _r


@LINKED_DATA.route("/comid/position")
async def flowline_by_position():
    """Find flowline by spatial search."""
    db = flask.current_app.NLDI_CONFIG.db
    base_url = flask.current_app.NLDI_CONFIG.server.base_url
    if (coords := flask.request.args.get("coords")) is None:
        LOGGER.error("No coordinates provided")
        return flask.Response(status=http.HTTPStatus.BAD_REQUEST, response="No coordinates provided")

    # Step 1: Get the COMID of the catchment polygon holding the point.
    async with AsyncSession(bind=db.async_engine) as db_session:
        async with services.CatchmentService.new(session=db_session) as catchment_svc:
            try:
                catchment = await catchment_svc.get_by_wkt_point(coords)
                comid = int(catchment.featureid)
            except ValueError as e:
                raise UnprocessableEntity(description=str(e))
            except NotFoundError as e:
                raise NotFound(description=str(e))
    # Step2: use that catchment's COMID to lookup flowline
    async with services.FlowlineService.new(session=db_session) as flowline_svc:
        flowline_feature = await flowline_svc.get_feature(
            comid,
            xtra_props={"navigation": util.url_join(base_url, "comid", comid, "navigation")},
        )
    _r = flask.Response(
        headers={"Content-Type": "application/json"},
        status=http.HTTPStatus.OK,
        response=util.stream_j2_template("FeatureCollection.j2", [msgspec.structs.asdict(flowline_feature)]),
    )
    return _r


# region Routes Per-Source
@LINKED_DATA.route("/<path:source_name>/<path:identifier>")
async def get_feature_by_identifier(source_name: str, identifier: str):
    db = flask.current_app.NLDI_CONFIG.db
    base_url = flask.current_app.NLDI_CONFIG.server.base_url

    async with AsyncSession(bind=db.async_engine) as db_session:
        async with services.FeatureService.new(session=db_session) as feature_svc:
            try:
                feature = await feature_svc.feature_lookup(source_name, identifier)
            except NotFoundError :
                raise NotFound(description=f"Not Found: {source_name}/{identifier}")
            nav_url = util.url_join(
                flask.current_app.NLDI_CONFIG.server.base_url, "linked-data", source_name, identifier, "navigation"
            )
            _geojson = feature.as_feature(excl_props=["crawler_source_id"], xtra_props={"navigation": nav_url})
            _r = flask.Response(
                headers={"Content-Type": "application/json"},
                status=http.HTTPStatus.OK,
                response=util.stream_j2_template("FeatureCollection.j2", [msgspec.to_builtins(_geojson)]),
            )
    return _r


@LINKED_DATA.route("/<path:source_name>/<path:identifier>/basin")
async def get_basin_by_id(source_name: str, identifier: str) -> dict[str, Any]:
    db = flask.current_app.NLDI_CONFIG.db
    base_url = flask.current_app.NLDI_CONFIG.server.base_url
    simplified = flask.request.args.get("simplified", "True").lower() == "true"
    split = flask.request.args.get("splitCatchment", "False").lower() == "true"

    async with AsyncSession(bind=db.async_engine) as db_session:
        basin_svc = services.BasinService(session=db_session, pygeoapi_url=flask.current_app.NLDI_CONFIG.server.pygeoapi_url)
        featurelist = await basin_svc.get_by_id(identifier, source_name, simplified, split)
        _r = flask.Response(
            headers={"Content-Type": "application/json"},
            status=http.HTTPStatus.OK,
            response=util.stream_j2_template("FeatureCollection.j2", [msgspec.to_builtins(f) for f in featurelist]),
        )
    return _r


@LINKED_DATA.route("/<path:source_name>/<path:identifier>/navigation")
async def get_navigation_modes(source_name: str, identifier: str):
    db = flask.current_app.NLDI_CONFIG.db
    base_url = flask.current_app.NLDI_CONFIG.server.base_url
    async with AsyncSession(bind=db.async_engine) as db_session:
        async with services.CrawlerSourceService.new(session=db_session) as sources_svc:
            src_exists = await sources_svc.suffix_exists(source_name)
            if not src_exists:
                raise NotFound(description == f"No such source: {source_name}")

    nav_url = util.url_join(base_url, "linked-data", source_name, identifier, "navigation")
    content = {
        "upstreamMain": util.url_join(nav_url, "UM"),
        "upstreamTributaries": util.url_join(nav_url, "UT"),
        "downstreamMain": util.url_join(nav_url, "DM"),
        "downstreamDiversions": util.url_join(nav_url, "DD"),
    }
    return content


@LINKED_DATA.route("/<path:source_name>/<path:identifier>/navigation/<path:nav_mode>")
async def get_navigation_info(source_name: str, identifier: str, nav_mode: str) -> list[dict[str, str]]:
    db = flask.current_app.NLDI_CONFIG.db
    base_url = flask.current_app.NLDI_CONFIG.server.base_url
    nav_url = util.url_join(base_url, "linked-data", source_name, identifier, "navigation")

    async with AsyncSession(bind=db.async_engine) as db_session:
        async with services.CrawlerSourceService.new(session=db_session) as sources_svc:
            src_exists = await sources_svc.suffix_exists(source_name)
            if not src_exists:
                raise NotFound(description=f"No such source: {source_name}")

            content = [
                {
                    "source": "Flowlines",
                    "sourceName": "NHDPlus flowlines",
                    "features": util.url_join(nav_url, nav_mode, "flowlines"),
                }
            ]
            for source in await sources_svc.list():
                src_id = source.source_suffix
                content.append(
                    {
                        "source": src_id,
                        "sourceName": source.source_name,
                        "features": util.url_join(nav_url, nav_mode, src_id.lower()),
                    }
                )
    return content


@LINKED_DATA.route("/<path:source_name>/<path:identifier>/navigation/<path:nav_mode>/flowlines")
async def get_flowline_navigation(
    source_name: str,
    identifier: str,
    nav_mode: str,
):
    try:
        _d = flask.request.args["distance"]
        distance = float(_d)
    except KeyError as e:
        return flask.Response(status=http.HTTPStatus.BAD_REQUEST, response="No distance provided")
    except (TypeError, ValueError) as e:
        return flask.Response(status=http.HTTPStatus.BAD_REQUEST, response="Invalid distance provided")
    trim_start = False
    try:
        _t = flask.request.args["trimStart"]
        trim_start = _t.lower() == "true"
    except KeyError as e:
        trim_start = False
    except (TypeError, ValueError) as e:
        return flask.Response(status=http.HTTPStatus.BAD_REQUEST, response="Invalid trimStart provided")
    db = flask.current_app.NLDI_CONFIG.db
    async with AsyncSession(bind=db.async_engine) as db_session:
        async with services.NavigationService.new(session=db_session) as navigation_svc:
            try:
                features = await navigation_svc.walk_flowlines(source_name, identifier, nav_mode, distance, trim_start)
            except NotFoundError as e:
                raise NotFound(description=str(e))
            except ValueError as e:
                raise BadRequest(description=str(e))
            _r = flask.Response(
                headers={"Content-Type": "application/json"},
                status=http.HTTPStatus.OK,
                response=util.stream_j2_template("FeatureCollection.j2", [msgspec.to_builtins(f) for f in features]),
            )
    return _r


@LINKED_DATA.route("/<path:source_name>/<path:identifier>/navigation/<path:nav_mode>/<path:data_source>")
async def get_feature_navigation(
    source_name: str,
    identifier: str,
    nav_mode: str,
    data_source: str,
) -> struct_geojson.FeatureCollection:
    try:
        _d = flask.request.args["distance"]
        distance = float(_d)
    except KeyError as e:
        return flask.Response(status=http.HTTPStatus.BAD_REQUEST, response="No distance provided")
    except (TypeError, ValueError) as e:
        return flask.Response(status=http.HTTPStatus.BAD_REQUEST, response="Invalid distance provided")

    db = flask.current_app.NLDI_CONFIG.db
    async with AsyncSession(bind=db.async_engine) as db_session:
        async with services.NavigationService.new(session=db_session) as navigation_svc:
            try:
                features = await navigation_svc.walk_features(source_name, identifier, nav_mode, data_source, distance)
            except NotFoundError as e:
                raise NotFound(description=str(e))
            except ValueError as e:
                raise BadRequest(description=str(e))
            _r = flask.Response(
                headers={"Content-Type": "application/json"},
                status=http.HTTPStatus.OK,
                response=util.stream_j2_template("FeatureCollection.j2", [msgspec.to_builtins(f) for f in features]),
            )
    return _r
