#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""Linked data controller for NLDI API."""

import logging
import uuid
from collections.abc import AsyncGenerator, Callable
from time import perf_counter
from typing import Annotated

import msgspec
from advanced_alchemy.exceptions import NotFoundError
from litestar import Controller, Response, get
from litestar.connection import Request
from litestar.di import Provide
from litestar.exceptions import ClientException, NotFoundException, ServiceUnavailableException, ValidationException
from litestar.openapi.spec.example import Example
from litestar.params import Parameter
from litestar.response import Stream
from litestar.types import ASGIApp, Receive, Scope, Send
from sqlalchemy.ext.asyncio import AsyncSession

from ... import util
from ...db.schemas import struct_geojson as geojson
from .. import AppState
from . import services
from .services.navigation import NAV_DIST_DEFAULTS


def _wants_html(request: Request) -> bool:
    """Returns True if the client specifically requested HTML (not JSON)."""
    f = request.query_params.get("f", "")
    if f in ("json", "jsonld"):
        return False
    accept = request.headers.get("Accept", "")
    return f == "html" or "text/html" in accept


def _html_redirect_response(request: Request) -> Response:
    """Returns an HTML page redirecting the client to the JSON version."""
    params = dict(request.query_params)
    params["f"] = "json"
    qstring = "&".join(f"{k}={v}" for k, v in params.items())
    new_url = f"{request.url.path}?{qstring}"
    return Response(
        content=f"""<html>An HTML representation is not available.
        <br/>See the data as JSON: <a href="{new_url}">{new_url}</a></html>""",
        media_type="text/html",
        status_code=200,
    )


def _html_redirect_if_wanted(request: Request) -> Response | None:
    if _wants_html(request):
        logging.info(f"Redirecting HTML->JSON: {request.url.path}")
        return _html_redirect_response(request)
    return None


def timing_middleware_factory(app: ASGIApp) -> ASGIApp:
    async def endpoint_timer(scope: Scope, receive: Receive, send: Send) -> None:
        req_id = uuid.uuid4().hex[:8]
        _start = perf_counter()
        logging.info(f"[{req_id}] {scope['method']} {scope['path']}?{scope.get('query_string', b'').decode()} - started")
        try:
            await app(scope, receive, send)
        except (ConnectionError, TimeoutError, OSError) as e:
            logging.warning(f"[{req_id}] Connection lost during {scope['method']} {scope['path']}: {e}")
        finally:
            _end = perf_counter()
            logging.info(f"[{req_id}] {scope['method']} {scope['path']}: {(_end - _start):.3f} seconds")

    return endpoint_timer


def _get_session_maker(request: Request) -> Callable[[], AsyncSession]:
    """Retrieve the SQLAlchemy session factory from app state."""
    state = dict(request.app.state)
    key = next(k for k in state if k.startswith("session_maker_class"))
    return state[key]


async def provide_basin_svc(db_session: AsyncSession, state: AppState) -> services.BasinService:
    return services.BasinService(session=db_session, pygeoapi_url=state.nldi_config.server.pygeoapi_url)


async def provide_catchment_svc(db_session: AsyncSession) -> services.CatchmentService:
    return services.CatchmentService(session=db_session)


async def provide_feature_svc(db_session: AsyncSession) -> services.FeatureService:
    return services.FeatureService(session=db_session)


async def provide_flowline_svc(db_session: AsyncSession) -> services.FlowlineService:
    return services.FlowlineService(session=db_session)


async def provide_navigation_svc(db_session: AsyncSession) -> services.NavigationService:
    return services.NavigationService(session=db_session)


async def provide_pygeoapi_svc(db_session: AsyncSession) -> services.PyGeoAPIService:
    return services.PyGeoAPIService(session=db_session)


async def provide_sources_svc(db_session: AsyncSession) -> services.CrawlerSourceService:
    return services.CrawlerSourceService(session=db_session)


async def provide_base_url(state: AppState) -> str:
    return state.nldi_config.server.base_url


# region: response objects
class DataSource(msgspec.Struct):
    source: str
    sourceName: str  # noqa: N815
    features: str


opi_sources_examples = [
    Example(id="comid", value="comid"),
    Example(id="wqp", value="wqp"),
]


opi_id_examples = [
    Example(id="comid", value="13293396"),
    Example(id="wqp", value="USGS-05427930"),
]


# region: Route definition
class LinkedDataController(Controller):
    path = "/linked-data"
    before_request = _html_redirect_if_wanted
    dependencies = {
        "sources_svc": Provide(provide_sources_svc),
        "pygeoapi_svc": Provide(provide_pygeoapi_svc),
        "flowline_svc": Provide(provide_flowline_svc),
        "catchment_svc": Provide(provide_catchment_svc),
        "feature_svc": Provide(provide_feature_svc),
        "basin_svc": Provide(provide_basin_svc),
        "navigation_svc": Provide(provide_navigation_svc),
        "base_url": Provide(provide_base_url),
    }
    middleware = [timing_middleware_factory]

    @get("/", tags=["nldi"])
    async def list_sources(self, base_url: str, sources_svc: services.CrawlerSourceService) -> list[DataSource]:
        """
        List all data sources.

        Produces a list of sources found in the NLDI database.  Sources include a
        property, ``features`` which is the link to the features that we know about,
        extracted from the named datasource.
        """

        src_list = await sources_svc.list()

        _rv = [
            {
                "source": "comid",
                "sourceName": "NHDPlus comid",
                "features": f"{base_url}/linked-data/comid",
            }
        ]
        for f in src_list:
            _rv.append(
                DataSource(
                    features=f"{base_url}/linked-data/{f.source_suffix}",
                    source=f.source_suffix,
                    sourceName=f.source_name,
                )
            )
        return _rv

    @get("/hydrolocation", tags=["nldi"])
    async def get_hydrolocation(
        self,
        base_url: str,
        pygeoapi_svc: services.PyGeoAPIService,
        coords: Annotated[
            str,
            Parameter(title="Coordinates as WKT string", examples=[Example(id="point", value="POINT(-89.509 43.087)")]),
        ],
    ) -> Response[geojson.FeatureCollection]:
        """
        Return the hydrologic location closest to a provided set of coordinates.

        The coordinates are provided as WKT-formatted string.
        """
        logging.debug(f"get_hydrolocation({base_url=}, {coords=})")
        try:
            features = await pygeoapi_svc.hydrolocation_by_coords(coords, base_url=base_url)
        except RuntimeError as e:
            raise ServiceUnavailableException(detail=str(e))
        except KeyError as e:
            raise NotFoundException(detail=str(e))

        return Response(
            # Should be only one.... no stream, just render and go.
            content=util.render_j2_template("FeatureCollection.j2", [msgspec.structs.asdict(f) for f in features]),
            media_type="application/json",
            status_code=200,
        )

    @get("/comid/position", tags=["by_comid"])
    async def flowline_by_position(
        self,
        base_url: str,
        catchment_svc: services.CatchmentService,
        flowline_svc: services.FlowlineService,
        coords: Annotated[
            str,
            Parameter(title="Coordinates as WKT string", examples=[Example(id="point", value="POINT(-89.509 43.087)")]),
        ],
    ) -> Response[geojson.FeatureCollection]:
        """
        Find flowline by spatial search.

        The supplied point (in WKT format) is expected in NAD83 longitude and latitude values. This
        point is used to locate a ``catchment`` by spatial intersection. That catchment is linked
        to the corresponding flowline by its comid.
        """

        logging.debug(f"flowline_by_position({base_url=}, {coords=})")

        try:
            catchment = await catchment_svc.get_by_wkt_point(coords)
            if not catchment:
                raise NotFoundException(detail=f"No catchment found at coords {coords}")
            comid = int(catchment.featureid)
        except ValueError as e:
            raise ValidationException(detail=str(e))
        except NotFoundError as e:
            raise NotFoundException(detail=str(e))

        try:
            flowline_feature = await flowline_svc.get_feature(
                comid,
                xtra_props={"navigation": util.url_join(base_url, "linked-data/comid", comid, "navigation")},
            )
        except (KeyError, NotFoundError):
            raise NotFoundException(detail=f"No Flowline for COMID {comid} at {coords}")

        return Response(
            # Should be only one.... no stream, just render and go.
            content=util.render_j2_template("FeatureCollection.j2", [msgspec.structs.asdict(flowline_feature)]),
            media_type="application/json",
            status_code=200,
        )

    @get("/{source_name:str}", tags=["by_sourceid"])
    async def list_features_by_source(
        self,
        request: Request,
        base_url: str,
        source_name: Annotated[str, Parameter(title="Source Identifier", examples=opi_sources_examples)],
        f: str = "",
        limit: int = 0,
        offset: int = 0,
    ) -> Response[geojson.FeatureCollection]:
        """
        List all features for a named source.

        The named source is retrieved as a FeatureCollection.  All features are returned.  The
        size of the return can be limited by specifying a ``limit`` parameter.  The ``offset`` can
        also be provided as part of the query.  In this way, you can step through all features
        in batches.
        """

        logging.debug(f"list_features_by_source({base_url=}, {source_name=}, {limit=}, {offset=})")

        _template = "FeatureCollectionGraph.j2" if f == "jsonld" else "FeatureCollection.j2"
        session_maker = _get_session_maker(request)

        async def _stream() -> AsyncGenerator[str, None]:
            try:
                async with session_maker() as session:
                    if source_name == "comid":
                        svc = services.FlowlineService(session=session)
                        feature_iterator = svc.feature_iterator(base_url=base_url, limit=limit, offset=offset)
                    else:
                        svc = services.FeatureService(session=session)
                        feature_iterator = svc.iter_by_src(source_name, base_url=base_url, limit=limit, offset=offset)
                    async for chunk in util.async_stream_j2_template(_template, feature_iterator):
                        yield chunk
            except (ConnectionError, TimeoutError, OSError) as e:
                logging.warning(f"Stream interrupted (client disconnect or timeout): {e}")
            except Exception as e:
                logging.error(f"Unexpected error during stream: {e}", exc_info=True)

        return Stream(
            _stream(),
            media_type="application/json",
            status_code=200,
        )

    @get("/{source_name:str}/{identifier:str}", tags=["by_sourceid"])
    async def get_feature_by_identifier(
        self,
        base_url: str,
        feature_svc: services.FeatureService,
        flowline_svc: services.FlowlineService,
        source_name: Annotated[str, Parameter(title="Source Identifier", examples=opi_sources_examples)],
        identifier: Annotated[str, Parameter(title="Feature Identifier", examples=opi_id_examples)],
        f: str = "",
    ) -> Response[geojson.FeatureCollection]:
        """
        Get a single feature by source name and identifier.

        A single source is queried, but note that the return is still a feature collection.
        """

        logging.debug(f"get_feature_by_identifier({base_url=}, {source_name=}, {identifier=})")

        _template = "FeatureCollectionGraph.j2" if f == "jsonld" else "FeatureCollection.j2"
        if source_name == "comid":
            try:
                _comid = int(identifier)  # < COMIDs are integers
                flowline_feature = await flowline_svc.get_feature(
                    identifier,
                    xtra_props={"navigation": util.url_join(base_url, "linked-data/comid", _comid, "navigation")},
                )
            except ValueError as e:
                raise ClientException(detail=f"Not a valid comid: {identifier}") from e
            except NotFoundError:
                raise NotFoundException(detail=f"COMID {_comid} not found.")

            return Response(
                # Should be only one.... no stream, just render and go.
                content=util.render_j2_template("FeatureCollection.j2", [msgspec.structs.asdict(flowline_feature)]),
                media_type="application/json",
                status_code=200,
            )
        else:
            try:
                feature = await feature_svc.feature_lookup(source_name, identifier)
            except NotFoundError:
                raise NotFoundException(detail=f"Feature ID {identifier} does not exist in source {source_name}.")

            nav_url = util.url_join(base_url, "linked-data", source_name, identifier, "navigation")
            _geojson = feature.as_feature(excl_props=["crawler_source_id"], xtra_props={"navigation": nav_url})

            return Response(
                # Should be only one.... no stream, just render and go.
                content=util.render_j2_template(_template, [msgspec.to_builtins(_geojson)]),
                media_type="application/json",
                status_code=200,
            )

    @get("/{source_name:str}/{identifier:str}/basin", tags=["by_sourceid"])
    async def get_basin_by_id(
        self,
        state: AppState,
        basin_svc: services.BasinService,
        source_name: Annotated[str, Parameter(title="Source Identifier", examples=opi_sources_examples)],
        identifier: Annotated[str, Parameter(title="Feature Identifier", examples=opi_id_examples)],
        simplified: Annotated[bool, Parameter(title="simplify geometry")] = True,
        split_catchment: Annotated[bool, Parameter(query="splitCatchment")] = False,
    ) -> Response[geojson.FeatureCollection]:
        """Compute upstream basin polygon for a source/identifier."""
        logging.debug(f"get_basin_by_id({source_name=}, {identifier=}, {simplified=}, {split_catchment=})")

        pygeoapi_url = state.nldi_config.server.pygeoapi_url
        try:
            featurelist = await basin_svc.get_by_id(identifier, source_name, simplified, split_catchment)
        except LookupError as e:
            raise NotFoundException(detail=str(e))
        except Exception:
            logging.exception("Unable to get/split basin")
            raise ServiceUnavailableException(detail="Unable to get/split basin")

        return Response(
            content=util.render_j2_template("FeatureCollection.j2", [msgspec.to_builtins(f) for f in featurelist]),
            media_type="application/json",
            status_code=200,
        )

    @get(path="/{source_name:str}/{identifier:str}/navigation", tags=["by_sourceid"])
    async def get_navigation_modes(
        self,
        base_url: str,
        source_name: Annotated[str, Parameter(title="Source Identifier", examples=opi_sources_examples)],
        identifier: Annotated[str, Parameter(title="Feature Identifier", examples=opi_id_examples)],
        sources_svc: services.CrawlerSourceService,
        f: str,
    ) -> dict:
        """Return navigation mode URLs for a given source/identifier."""

        logging.debug(f"get_navigation_modes({base_url=}, {source_name=}, {identifier=})")

        if not await sources_svc.suffix_exists(source_name):
            raise NotFoundException(detail=f"No such source: {source_name}")

        nav_url = util.url_join(base_url, "linked-data", source_name, identifier, "navigation")
        return {
            "upstreamMain": util.url_join(nav_url, "UM"),
            "upstreamTributaries": util.url_join(nav_url, "UT"),
            "downstreamMain": util.url_join(nav_url, "DM"),
            "downstreamDiversions": util.url_join(nav_url, "DD"),
        }

    @get("/{source_name:str}/{identifier:str}/navigation/{nav_mode:str}", tags=["by_sourceid"])
    async def get_navigation_info(
        self,
        base_url: str,
        source_name: Annotated[str, Parameter(title="Source Identifier", examples=opi_sources_examples)],
        identifier: Annotated[str, Parameter(title="Feature Identifier", examples=opi_id_examples)],
        nav_mode: str,
        sources_svc: services.CrawlerSourceService,
    ) -> list[dict]:
        """List data sources available for navigation."""

        logging.debug(f"get_navigation_info({base_url=}, {source_name=}, {identifier=}, {nav_mode=})")

        nav_url = util.url_join(base_url, "linked-data", source_name, identifier, "navigation")

        if not await sources_svc.suffix_exists(source_name):
            raise NotFoundException(detail=f"No such source: {source_name}")

        src_list = await sources_svc.list()
        content = [
            {
                "source": "Flowlines",
                "sourceName": "NHDPlus flowlines",
                "features": util.url_join(nav_url, nav_mode, "flowlines"),
            }
        ]
        for source in src_list:
            content.append(
                {
                    "source": source.source_suffix,
                    "sourceName": source.source_name,
                    "features": util.url_join(nav_url, nav_mode, source.source_suffix.lower()),
                }
            )
        return content

    @get("/{source_name:str}/{identifier:str}/navigation/{nav_mode:str}/flowlines", tags=["by_sourceid"])
    async def get_flowline_navigation(
        self,
        request: Request,
        source_name: Annotated[str, Parameter(title="Source Identifier", examples=opi_sources_examples)],
        identifier: Annotated[str, Parameter(title="Feature Identifier", examples=opi_id_examples)],
        nav_mode: str,
        distance: float | None = None,
        trim_start: Annotated[bool, Parameter(query="trimStart")] = False,
        exclude_geom: Annotated[bool, Parameter(query="excludeGeometry")] = False,
    ) -> Response[geojson.FeatureCollection]:
        """Navigate flowlines from source/identifier."""
        logging.debug(
            f"get_flowline_navigation({source_name=}, {identifier=}, {nav_mode=}, {distance=}, {trim_start=}, {exclude_geom=})"
        )

        _distance = distance if distance is not None else NAV_DIST_DEFAULTS.get(nav_mode, 100)
        session_maker = _get_session_maker(request)

        async with session_maker() as session:
            try:
                await services.NavigationService(session=session).validate_start(source_name, identifier, nav_mode, trim_start)
            except NotFoundError as e:
                raise NotFoundException(detail=str(e))
            except ValueError as e:
                raise ValidationException(detail=str(e))

        async def _stream() -> AsyncGenerator[str, None]:
            try:
                async with session_maker() as session:
                    features = await services.NavigationService(session=session).walk_flowlines(
                        source_name, identifier, nav_mode, _distance, trim_start
                    )

                    async def feature_stream():
                        async for feat in features:
                            if exclude_geom:
                                feat.geometry = {}
                            yield msgspec.to_builtins(feat)

                    async for chunk in util.async_stream_j2_template("FeatureCollection.j2", feature_stream()):
                        yield chunk
            except (ConnectionError, TimeoutError, OSError) as e:
                logging.warning(f"Stream interrupted (client disconnect or timeout): {e}")
            except Exception as e:
                logging.error(f"Unexpected error during stream: {e}", exc_info=True)

        return Stream(
            _stream(),
            media_type="application/json",
            status_code=200,
        )

    @get("/{source_name:str}/{identifier:str}/navigation/{nav_mode:str}/{data_source:str}", tags=["by_sourceid"])
    async def get_feature_navigation(
        self,
        request: Request,
        source_name: Annotated[str, Parameter(title="Source Identifier", examples=opi_sources_examples)],
        identifier: Annotated[str, Parameter(title="Feature Identifier", examples=opi_id_examples)],
        nav_mode: str,
        data_source: str,
        f: str = "",
        distance: float | None = None,
        exclude_geom: Annotated[bool, Parameter(query="excludeGeometry")] = False,
    ) -> Response[geojson.FeatureCollection]:
        """Navigate features of a data source."""

        logging.debug(
            f"get_feature_navigation({source_name=}, {identifier=}, {nav_mode=}, {data_source=}, {distance=}, {exclude_geom=})"
        )

        _template = "FeatureCollectionGraph.j2" if f == "jsonld" else "FeatureCollection.j2"
        _distance = distance if distance is not None else NAV_DIST_DEFAULTS.get(nav_mode, 100)
        session_maker = _get_session_maker(request)

        async with session_maker() as session:
            try:
                await services.NavigationService(session=session).validate_start(source_name, identifier, nav_mode)
            except NotFoundError as e:
                raise NotFoundException(detail=str(e))
            except ValueError as e:
                raise ValidationException(detail=str(e))

        async def _stream() -> AsyncGenerator[str, None]:
            try:
                async with session_maker() as session:
                    features = await services.NavigationService(session=session).walk_features(
                        source_name, identifier, nav_mode, data_source, _distance
                    )

                    async def _feature_stream():
                        async for feat in features:
                            if exclude_geom:
                                feat.geometry = {}
                            yield msgspec.to_builtins(feat)

                    async for chunk in util.async_stream_j2_template(_template, _feature_stream()):
                        yield chunk
            except (ConnectionError, TimeoutError, OSError) as e:
                logging.warning(f"Stream interrupted (client disconnect or timeout): {e}")
            except Exception as e:
                logging.error(f"Unexpected error during stream: {e}", exc_info=True)

        return Stream(
            _stream(),
            media_type="application/json",
            status_code=200,
        )
