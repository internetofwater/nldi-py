#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""Routers/blueprints for flask app endpoints related to linked data, navigation, etc."""

import http
import json
import logging
import traceback
from copy import deepcopy
from typing import Any, Literal, TypeVar

import flask
import msgspec
from advanced_alchemy.exceptions import NotFoundError
from werkzeug.exceptions import BadRequest, HTTPException, NotFound, ServiceUnavailable, UnprocessableEntity

from ... import __version__, util
from ...config import MasterConfig, status
from ...db.schemas import struct_geojson
from . import services
from .services.navigation import NAV_DIST_DEFAULTS

LINKED_DATA = flask.Blueprint("linked-data", __name__)


class HtmlJsonException(Exception):  # noqa: N818
    pass


def link_header(r: flask.Request, offset: int, limit: int, maxcount: int) -> dict:
    if limit <= 0:
        return dict()

    next_offset = offset + limit
    last_offset = maxcount - (maxcount % limit)

    if next_offset > maxcount:
        # There is no next; we're already on the last page.
        hdr = dict()
    else:
        next_ = f'<{r.base_url}?f={r.format}&limit={limit}&offset={next_offset}>;rel="next"'
        # last_ = f'<{r.base_url}?f={r.format}&limit={limit}&offset={last_offset}>;rel="last"'
        hdr = {"Link": next_}
    return hdr


@LINKED_DATA.errorhandler(HtmlJsonException)
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


@LINKED_DATA.errorhandler(HTTPException)
def jsonify_exception_message(e) -> flask.Response:
    response = e.get_response()
    response.data = json.dumps(
        {
            "type": "error",
            "detail": e.description,
        }
    )
    response.content_type = "application/json"
    return response


@LINKED_DATA.before_request
def parse_incoming_request() -> None:
    rp = flask.request.path
    if rp != "/" and rp.endswith("/"):
        return flask.redirect(rp[:-1])

    if flask.request.args.get("f") in ["json", "jsonld"]:
        logging.debug(f"JSON specifically requested")
        flask.request.format = flask.request.args.get("f")
        return
    # NOTE: This is a special request for the interface:  If the requesting client specifically calls out
    # that it accepts HTML (as opposed to */*), we are assuming that it is a web browser or other
    # general-purpose client. We want them to specifically ask for JSON with the `f=json` query param.
    _html_specified = "text/html" in flask.request.headers.get("Accept", "")
    if flask.request.args.get("f") == "html" or _html_specified:
        _q = dict(flask.request.args)
        _q["f"] = "json"
        _qstring = "&".join([f"{k}={v}" for k, v in _q.items()])
        logging.debug(f"REDIRECT from HTML")
        new_url = f"{rp}?{_qstring}"
        raise HtmlJsonException(new_url)
    flask.request.format = "json"


@LINKED_DATA.route("/")
def list_sources():
    base_url = flask.current_app.NLDI_CONFIG.server.base_url
    with flask.current_app.alchemy.with_session() as db_session:
        sources_svc = services.CrawlerSourceService(session=db_session)
        src_list = sources_svc.list()
        _r = list(src_list)
    _rv = [
        {
            "source": "comid",
            "sourceName": "NHDPlus comid",
            "features": f"{base_url}/linked-data/comid",
        }
    ]
    for f in _r:
        _rv.append(
            dict(
                features=f"{base_url}/linked-data/{f.source_suffix}",
                source=f.source_suffix,
                sourceName=f.source_name,
            )
        )
    return _rv


@LINKED_DATA.route("/hydrolocation")
def get_hydrolocation():
    if (coords := flask.request.args.get("coords")) is None:
        return flask.Response(status=http.HTTPStatus.BAD_REQUEST, response="No coordinates provided")
    db = flask.current_app.NLDI_CONFIG.db
    base_url = flask.current_app.NLDI_CONFIG.server.base_url

    with flask.current_app.alchemy.with_session() as db_session:
        pygeoapi_svc = services.PyGeoAPIService(session=db_session)
        try:
            features = pygeoapi_svc.hydrolocation_by_coords(coords, base_url=base_url)
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


@LINKED_DATA.route("/comid")
def get_all_flowlines():
    base_url = flask.current_app.NLDI_CONFIG.server.base_url
    if flask.request.format == "jsonld":
        _template = "FeatureCollectionGraph.j2"
    else:
        _template = "FeatureCollection.j2"

    try:
        _limit = int(flask.request.args.get("limit", 0))
        _offset = int(flask.request.args.get("offset", 0))
    except ValueError:
        raise BadRequest(f"limit and offset must be integers") from None

    with flask.current_app.alchemy.with_session() as db_session:
        flowline_svc = services.FlowlineService(session=db_session)
        # List all features in the named source
        feature_iterator = flowline_svc.feature_iterator(base_url=base_url, limit=_limit, offset=_offset)
        _featurecount = flowline_svc.count()
        _limit = _limit or _featurecount
        _link_hdr = link_header(flask.request, offset=_offset, limit=_limit, maxcount=_featurecount)
        # _link_hdr.update({"Content-Type": "application/json"})
        _r = flask.Response(
            headers=_link_hdr,
            status=http.HTTPStatus.OK,
            mimetype="application/json",
            response=util.stream_j2_template(_template, feature_iterator),
        )
    return _r


@LINKED_DATA.route("/comid/<int:comid>")
def get_flowline_by_comid(comid: int | None = None):
    base_url = flask.current_app.NLDI_CONFIG.server.base_url
    try:
        _comid = int(comid)
    except Exception as e:
        raise BadRequest(f"Could not make {comid} an integer") from None

    with flask.current_app.alchemy.with_session() as db_session:
        flowline_svc = services.FlowlineService(session=db_session)
        try:
            flowline_feature = flowline_svc.get_feature(
                comid,
                xtra_props={"navigation": util.url_join(base_url, "linked-data/comid", comid, "navigation")},
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
def flowline_by_position():
    """Find flowline by spatial search."""
    db = flask.current_app.NLDI_CONFIG.db
    base_url = flask.current_app.NLDI_CONFIG.server.base_url
    if (coords := flask.request.args.get("coords")) is None:
        logging.error("No coordinates provided")
        return flask.Response(status=http.HTTPStatus.BAD_REQUEST, response="No coordinates provided")

    with flask.current_app.alchemy.with_session() as db_session:
        # Step 1: Get the COMID of the catchment polygon holding the point.
        catchment_svc = services.CatchmentService(session=db_session)
        try:
            catchment = catchment_svc.get_by_wkt_point(coords)
            comid = int(catchment.featureid)
        except ValueError as e:
            raise UnprocessableEntity(description=str(e))
        except NotFoundError as e:
            raise NotFound(description=str(e))

        # Step2: use that catchment's COMID to lookup flowline
        flowline_svc = services.FlowlineService(session=db_session)
        flowline_feature = flowline_svc.get_feature(
            comid,
            xtra_props={"navigation": util.url_join(base_url, "linked-data/comid", comid, "navigation")},
        )
        _r = flask.Response(
            headers={"Content-Type": "application/json"},
            status=http.HTTPStatus.OK,
            response=util.stream_j2_template("FeatureCollection.j2", [msgspec.structs.asdict(flowline_feature)]),
        )
    return _r


# region Routes Per-Source
@LINKED_DATA.route("/<path:source_name>")
@LINKED_DATA.route("/<path:source_name>/<path:identifier>")
def get_feature_by_identifier(source_name: str, identifier: str = ""):
    base_url = flask.current_app.NLDI_CONFIG.server.base_url
    if flask.request.format == "jsonld":
        _template = "FeatureCollectionGraph.j2"
    else:
        _template = "FeatureCollection.j2"

    try:
        _limit = int(flask.request.args.get("limit", 0))
        _offset = int(flask.request.args.get("offset", 0))
    except ValueError:
        raise BadRequest(f"limit and offset must be integers") from None

    with flask.current_app.alchemy.with_session() as db_session:
        feature_svc = services.FeatureService(session=db_session)
        if not identifier:
            # List all features in the named source
            _featurecount = feature_svc.featurecount(source_name)
            _limit = _limit or _featurecount
            feature_iterator = feature_svc.iter_by_src(
                source_name,
                base_url=base_url,
                limit=_limit,
                offset=_offset,
            )
            _link_hdr = link_header(flask.request, offset=_offset, limit=_limit, maxcount=_featurecount)
            _r = flask.Response(
                headers=_link_hdr,
                response=util.stream_j2_template(_template, feature_iterator),
                mimetype="application/json",
                status=http.HTTPStatus.OK,
            )
        else:
            try:
                feature = feature_svc.feature_lookup(source_name, identifier)
            except NotFoundError:
                raise NotFound(description=f"Feature ID {identifier} does not exist in source {source_name}.")
            nav_url = util.url_join(
                flask.current_app.NLDI_CONFIG.server.base_url, "linked-data", source_name, identifier, "navigation"
            )
            _geojson = feature.as_feature(excl_props=["crawler_source_id"], xtra_props={"navigation": nav_url})
            _r = flask.Response(
                headers={"Content-Type": "application/json"},
                status=http.HTTPStatus.OK,
                response=util.stream_j2_template(_template, [msgspec.to_builtins(_geojson)]),
            )
    return _r


@LINKED_DATA.route("/<path:source_name>/<path:identifier>/basin")
def get_basin_by_id(source_name: str, identifier: str) -> dict[str, Any]:
    db = flask.current_app.NLDI_CONFIG.db
    base_url = flask.current_app.NLDI_CONFIG.server.base_url
    simplified = flask.request.args.get("simplified", "True").lower() == "true"
    split = flask.request.args.get("splitCatchment", "False").lower() == "true"

    with flask.current_app.alchemy.with_session() as db_session:
        basin_svc = services.BasinService(
            session=db_session,
            pygeoapi_url=flask.current_app.NLDI_CONFIG.server.pygeoapi_url,
        )
        try:
            featurelist = basin_svc.get_by_id(identifier, source_name, simplified, split)
        except Exception as e:
            logging.exception("Unable to get/split basin")
            raise ServiceUnavailable("Unable to get/split basin") from e

        _r = flask.Response(
            headers={"Content-Type": "application/json"},
            status=http.HTTPStatus.OK,
            response=util.stream_j2_template("FeatureCollection.j2", [msgspec.to_builtins(f) for f in featurelist]),
        )
    return _r


@LINKED_DATA.route("/<path:source_name>/<path:identifier>/navigation")
def get_navigation_modes(source_name: str, identifier: str):
    db = flask.current_app.NLDI_CONFIG.db
    base_url = flask.current_app.NLDI_CONFIG.server.base_url

    with flask.current_app.alchemy.with_session() as db_session:
        sources_svc = services.CrawlerSourceService(session=db_session)
        src_exists = sources_svc.suffix_exists(source_name)
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
def get_navigation_info(source_name: str, identifier: str, nav_mode: str) -> list[dict[str, str]]:
    db = flask.current_app.NLDI_CONFIG.db
    base_url = flask.current_app.NLDI_CONFIG.server.base_url
    nav_url = util.url_join(base_url, "linked-data", source_name, identifier, "navigation")

    with flask.current_app.alchemy.with_session() as db_session:
        sources_svc = services.CrawlerSourceService(session=db_session)
        src_exists = sources_svc.suffix_exists(source_name)
        if not src_exists:
            raise NotFound(description == f"No such source: {source_name}")

    content = [
        {
            "source": "Flowlines",
            "sourceName": "NHDPlus flowlines",
            "features": util.url_join(nav_url, nav_mode, "flowlines"),
        }
    ]
    for source in sources_svc.list():
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
def get_flowline_navigation(
    source_name: str,
    identifier: str,
    nav_mode: str,
):
    try:
        _d = flask.request.args["distance"]
        if _d:
            distance = float(_d)
        else:
            distance = NAV_DIST_DEFAULTS.get(nav_mode, 100)
    except KeyError as e:
        distance = NAV_DIST_DEFAULTS.get(nav_mode, 100)
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

    with flask.current_app.alchemy.with_session() as db_session:
        navigation_svc = services.NavigationService(session=db_session)

        try:
            features = navigation_svc.walk_flowlines(source_name, identifier, nav_mode, distance, trim_start)
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
def get_feature_navigation(
    source_name: str,
    identifier: str,
    nav_mode: str,
    data_source: str,
) -> struct_geojson.FeatureCollection:
    if flask.request.format == "jsonld":
        _template = "FeatureCollectionGraph.j2"
    else:
        _template = "FeatureCollection.j2"

    try:
        _d = flask.request.args["distance"]
        if _d:
            distance = float(_d)
        else:
            distance = NAV_DIST_DEFAULTS.get(nav_mode, 100)
    except KeyError as e:
        distance = NAV_DIST_DEFAULTS.get(nav_mode, 100)
    except (TypeError, ValueError) as e:
        return flask.Response(status=http.HTTPStatus.BAD_REQUEST, response="Invalid distance provided")

    with flask.current_app.alchemy.with_session() as db_session:
        navigation_svc = services.NavigationService(session=db_session)
        try:
            features = navigation_svc.walk_features(source_name, identifier, nav_mode, data_source, distance)
        except NotFoundError as e:
            raise NotFound(description=str(e))
        except ValueError as e:
            raise BadRequest(description=str(e))

    _r = flask.Response(
        headers={"Content-Type": "application/json"},
        status=http.HTTPStatus.OK,
        response=util.stream_j2_template(_template, [msgspec.to_builtins(f) for f in features]),
    )
    return _r
