#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""
Services for NLDI.

Under this model, "services" are the objects holding the business logic
surrounding a request.  The service uses the repository to find data,
but then applies its own logic/handling.  I think of the services
object as being an implementation of a unit-of-work pattern.
"""

import json
import logging
from collections.abc import AsyncGenerator, Generator

import msgspec
import sqlalchemy

# from advanced_alchemy.exceptions import NotFoundError
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from sqlalchemy import and_
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import Select

from nldi.db.schemas.nhdplus import FlowlineModel
from nldi.db.schemas.nldi_data import CrawlerSourceModel, FeatureSourceModel

from .... import util

# from .... import util
from ....db.schemas import struct_geojson
from .. import repos


class FlowlineService(SQLAlchemyAsyncRepositoryService[FlowlineModel]):
    repository_type = repos.FlowlineRepository

    async def get(self, id: str | int, *args, **kwargs) -> FlowlineModel:
        _id = int(id)  # Force the id as an integer; is there a better way to do this?
        return await super().get(_id, *args, **kwargs)

    async def get_feature(self, comid: str | int, xtra_props: dict[str, str] | None = None) -> struct_geojson.Feature:
        """
        Get a flowline by its comid.

        :param comid: Unique comid for the flowline
        :type comid: str | int
        :param xtra_props: Extra properties to attach to the feature, defaults to None
        :type xtra_props: dict[str, str] | None
        :return: A geojson feature with the specified comid
        :rtype: struct_geojson.Feature
        """
        _feature = await self.get(comid)

        ## Need to manipulate the properties key to match expectations.
        _result = _feature.as_feature(
            rename_fields={
                "permanent_identifier": "identifier",
                "nhdplus_comid": "comid",
            },
            xtra_props=xtra_props,
        )
        _result.id = _feature.nhdplus_comid
        return _result

    async def features_from_nav_query(self, nav_query: Select) -> AsyncGenerator[struct_geojson.Feature, None]:
        subq = nav_query.subquery()
        stmt = (
            sqlalchemy.select(FlowlineModel)
            .join(subq, FlowlineModel.nhdplus_comid == subq.c.comid)
            .execution_options(yield_per=100)
        )
        logging.debug("Feature Navigation SQL Query:")
        logging.debug(f"{stmt.compile()}")
        result = await self.repository.session.stream_scalars(stmt)
        try:
            async for f in result:
                yield f.as_feature(excl_props=["objectid", "permanent_identifier", "fmeasure", "tmeasure", "reachcode"])
        finally:
            await self.repository.session.close()

    async def trimed_features_from_nav_query(
        self, nav_query: Select, trim_query: Select
    ) -> AsyncGenerator[struct_geojson.Feature, None]:
        nav_subq = nav_query.subquery()
        trim_subq = trim_query.subquery()
        stmt = (
            sqlalchemy.select(FlowlineModel, trim_subq.c.trimmed_geojson)
            .join(nav_subq, FlowlineModel.nhdplus_comid == nav_subq.c.comid)
            .join(trim_subq, FlowlineModel.nhdplus_comid == trim_subq.c.comid)
            .execution_options(yield_per=100)
        )
        logging.debug("Feature Navigation (trimmed) SQL Query:")
        logging.debug(f"{stmt.compile()}")
        result = await self.repository.session.stream(stmt)
        try:
            async for f, g in result:
                _tmp = f.as_feature(excl_props=["objectid", "permanent_identifier", "fmeasure", "tmeasure", "reachcode"])
                _tmp.geometry = json.loads(g)
                yield _tmp
        finally:
            # This extra layer of try/finally is to force the closing of the db session, no matter what.
            await self.repository.session.close()

    async def feat_get_distance_from_flowline(self, feature_id: str, feature_source: str) -> float:
        x = (
            sqlalchemy.select([FlowlineModel.shape, FeatureSourceModel.location])
            .join(
                FeatureSourceModel,
                and_(
                    FeatureSourceModel.comid == FlowlineModel.nhdplus_comid,
                    FeatureSourceModel.identifier == sqlalchemy.text(":feature_id"),
                ),
            )
            .join(
                CrawlerSourceModel,
                sqlalchemy.and_(
                    CrawlerSourceModel.source_suffix == sqlalchemy.text(":feature_source"),
                    FeatureSourceModel.crawler_source_id == CrawlerSourceModel.crawler_source_id,  # noqa
                ),
            )
        )

        query = sqlalchemy.select([sqlalchemy.func.ST_Distance(x.c.location, x.c.shape, False)])
        stmt = query.params(feature_id=feature_id, feature_source=feature_source)
        logging.debug(stmt.compile())
        hits = await self.repository.session.execute(stmt)

        dist = hits.scalar()
        if dist is None:
            logging.debug("Not on flwline.")
            return None
        logging.debug("{feature_source}/{feature_id} is {dist} from a flowline")
        return dist

    async def feat_get_nearest_point_on_flowline(self, feature_id: str, feature_source: str) -> tuple[float, float]:
        """
        Interpolate a point on a flowline nearest to the named source/feature.

        :param feature_id: Unique ID of the feature to use as search.
        :type feature_id: str
        :param feature_source: The suffix of the source for this feature.
        :type feature_source: str
        :return: An x,y point along a Flowline which matches the named feature/source location.
        :rtype: tuple[float, float]
        """
        shapes = (
            sqlalchemy.select([FlowlineModel.shape.label("shape"), FeatureSourceModel.location.label("location")])
            .join(
                FeatureSourceModel,
                sqlalchemy.and_(
                    FeatureSourceModel.comid == FlowlineModel.nhdplus_comid,
                    FeatureSourceModel.identifier == sqlalchemy.text(":feature_id"),
                ),
            )
            .join(
                CrawlerSourceModel,
                sqlalchemy.and_(
                    CrawlerSourceModel.source_suffix == sqlalchemy.text(":feature_source"),
                    FeatureSourceModel.crawler_source_id == CrawlerSourceModel.crawler_source_id,
                ),
            )
            .alias("shapes")
        )

        point = sqlalchemy.select(
            [sqlalchemy.func.ST_Closestpoint(shapes.c.shape, shapes.c.location).label("point")]
        ).alias("point")

        query = sqlalchemy.select(
            [sqlalchemy.func.ST_X(point.c.point).label("lon"), sqlalchemy.func.ST_Y(point.c.point).label("lat")]
        ).alias("result")

        stmt = query.params(feature_id=feature_id, feature_source=feature_source)

        logging.debug(stmt.compile())
        hits = await self.repository.session.execute(stmt)

        pt = hits.fetchone()
        if pt is None or None in pt:
            logging.debug("Cannot find point on flowline.")
            return None
        logging.debug("{feature_source}/{feature_id} is closest to {pt} on flowline")
        return pt

    async def feat_get_point_along_flowline(self, feature_id: str, feature_source: str) -> tuple[float, float]:
        """
        Interpolate a point along the flowline, matching the named source/feature.

        :param feature_id: Unique ID of the feature to use as search.
        :type feature_id: str
        :param feature_source: The suffix of the source for this feature.
        :type feature_source: str
        :return: An x,y point along a Flowline which matches the named feature/source location.
        :rtype: tuple[float, float]
        """
        # Custom return data "column"
        point = sqlalchemy.func.ST_LineInterpolatePoint(
            FlowlineModel.shape,
            (
                1
                - (
                    (FeatureSourceModel.measure - FlowlineModel.fmeasure)
                    / (FlowlineModel.tmeasure - FlowlineModel.fmeasure)
                )
            ),
        )

        stmt = (
            sqlalchemy.select(sqlalchemy.func.ST_X(point).label("lon"), sqlalchemy.func.ST_Y(point).label("lat"))
            .join(
                FeatureSourceModel,
                sqlalchemy.and_(
                    FeatureSourceModel.comid == FlowlineModel.nhdplus_comid,
                    FeatureSourceModel.identifier == sqlalchemy.text(":feature_id"),
                ),
            )
            .join(
                CrawlerSourceModel,
                sqlalchemy.and_(
                    CrawlerSourceModel.source_suffix == sqlalchemy.text(":feature_source"),
                    FeatureSourceModel.crawler_source_id == CrawlerSourceModel.crawler_source_id,  # noqa
                ),
            )
        ).params(feature_id=feature_id, feature_source=feature_source)

        logging.debug("Feature Along Flowline SQL Query:")
        _query_stmt = stmt.compile()
        logging.debug(f"{_query_stmt}")

        hits = await self.repository._execute(stmt)

        pt = hits.fetchone()
        if pt is None or None in pt:
            logging.debug("Not on a flowline.")
            return None
        logging.debug("{feature_source}/{feature_id} matches {pt} on flowline")
        return pt

    async def feature_iterator(
        self, base_url: str = "", offset: int = 0, limit: int = 1000
    ) -> AsyncGenerator[dict, None]:
        """Provides a paginated response for the feature collection as an async generator.

        Rows are fetched from the database in batches of 100 (yield_per) and produced
        one at a time, enabling the caller to stream results without loading the full
        result set into memory before beginning.
        """
        stmt = (
            sqlalchemy.select(FlowlineModel)
            .order_by(FlowlineModel.nhdplus_comid)
            .offset(offset)
            .limit(limit)
            .execution_options(yield_per=100)
        )

        logging.debug("Feature Iterator SQL Query:")
        logging.debug(f"{stmt.compile()}")

        result = await self.repository.session.stream_scalars(stmt)
        try:
            async for f in result:
                nav_url = util.url_join(base_url, "linked-data/comid", f.nhdplus_comid, "navigation")
                yield msgspec.to_builtins(
                    f.as_feature(
                        rename_fields={
                            "permanent_identifier": "identifier",
                            "nhdplus_comid": "comid",
                        },
                        xtra_props={"navigation": nav_url},
                    )
                )
        finally:
            await self.repository.session.close()

def flowline_svc(db_session: Session) -> Generator[FlowlineService, None, None]:
    """Provider function as part of the dependency-injection mechanism."""
    with FlowlineService.new(session=db_session) as service:
        yield service
