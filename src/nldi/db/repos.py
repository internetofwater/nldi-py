# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Repositories for NLDI data access.

Thin wrappers around advanced-alchemy's async repository.
These are the boundary between the data model and the rest of the application.
"""

import geoalchemy2
import sqlalchemy
from advanced_alchemy.repository import SQLAlchemyAsyncRepository

from .models import CatchmentModel, CrawlerSourceModel, FeatureSourceModel, FlowlineModel


class CrawlerSourceRepository(SQLAlchemyAsyncRepository[CrawlerSourceModel]):
    """Repository for crawler source lookups."""

    model_type = CrawlerSourceModel
    id_attribute = "crawler_source_id"

    async def get_by_suffix(self, suffix: str) -> CrawlerSourceModel | None:
        """Look up a source by suffix, case-insensitive."""
        return await self.get_one_or_none(
            sqlalchemy.func.lower(CrawlerSourceModel.source_suffix) == suffix.lower(),
        )


class FeatureRepository(SQLAlchemyAsyncRepository[FeatureSourceModel]):
    """Repository for feature lookups."""

    model_type = FeatureSourceModel
    id_attribute = "identifier"

    async def feature_lookup(self, source_suffix: str, identifier: str) -> FeatureSourceModel | None:
        """Look up a feature by source suffix and identifier.

        Joins to crawler_source to filter by source_suffix.
        """
        return await self.get_one_or_none(
            sqlalchemy.func.lower(CrawlerSourceModel.source_suffix) == source_suffix.lower(),
            FeatureSourceModel.identifier == identifier,
            statement=sqlalchemy.select(FeatureSourceModel).join(
                CrawlerSourceModel,
                FeatureSourceModel.crawler_source_id == CrawlerSourceModel.crawler_source_id,
            ),
        )

    async def list_by_source(self, source_suffix: str, limit: int = 0, offset: int = 0) -> list[FeatureSourceModel]:
        """List features for a source, with optional pagination."""
        stmt = (
            sqlalchemy.select(FeatureSourceModel)
            .join(CrawlerSourceModel, FeatureSourceModel.crawler_source_id == CrawlerSourceModel.crawler_source_id)
            .where(sqlalchemy.func.lower(CrawlerSourceModel.source_suffix) == source_suffix.lower())
            .order_by(FeatureSourceModel.identifier)
            .offset(offset)
        )
        if limit > 0:
            stmt = stmt.limit(limit)
        return list(await self.list(statement=stmt))

    async def from_nav_query(self, data_source: str, nav_query: sqlalchemy.sql.Select) -> list[FeatureSourceModel]:
        """Execute a navigation CTE and join to features filtered by data source."""
        subq = nav_query.subquery()
        stmt = (
            sqlalchemy.select(FeatureSourceModel)
            .join(CrawlerSourceModel, FeatureSourceModel.crawler_source_id == CrawlerSourceModel.crawler_source_id)
            .join(subq, FeatureSourceModel.comid == subq.c.comid)
            .where(sqlalchemy.func.lower(CrawlerSourceModel.source_suffix) == data_source.lower())
        )
        return list(await self.list(statement=stmt))


class FlowlineRepository(SQLAlchemyAsyncRepository[FlowlineModel]):
    """Repository for flowline lookups."""

    model_type = FlowlineModel
    id_attribute = "nhdplus_comid"

    async def list_all(self, limit: int = 0, offset: int = 0) -> list[FlowlineModel]:
        """List flowlines with optional pagination."""
        stmt = sqlalchemy.select(FlowlineModel).order_by(FlowlineModel.nhdplus_comid).offset(offset)
        if limit > 0:
            stmt = stmt.limit(limit)
        return list(await self.list(statement=stmt))

    async def from_nav_query(self, nav_query: sqlalchemy.sql.Select) -> list[FlowlineModel]:
        """Execute a navigation CTE and join to flowlines."""
        subq = nav_query.subquery()
        stmt = sqlalchemy.select(FlowlineModel).join(subq, FlowlineModel.nhdplus_comid == subq.c.comid)
        return list(await self.list(statement=stmt))

    async def from_trimmed_nav_query(
        self, nav_query: sqlalchemy.sql.Select, trim_query: sqlalchemy.sql.Select
    ) -> list:  # list of (FlowlineModel, geojson_str) tuples
        """Execute navigation + trim queries, return flowlines with trimmed geometry."""
        nav_subq = nav_query.subquery()
        trim_subq = trim_query.subquery()
        stmt = (
            sqlalchemy.select(FlowlineModel, trim_subq.c.trimmed_geojson)
            .join(nav_subq, FlowlineModel.nhdplus_comid == nav_subq.c.comid)
            .join(trim_subq, FlowlineModel.nhdplus_comid == trim_subq.c.comid)
        )
        result = await self.session.execute(stmt)
        return list(result)


class CatchmentRepository(SQLAlchemyAsyncRepository[CatchmentModel]):
    """Repository for catchment lookups."""

    model_type = CatchmentModel
    id_attribute = "featureid"

    async def get_by_point(self, wkt_point: str) -> CatchmentModel | None:
        """Find a catchment by spatial intersection with a WKT point."""
        point = geoalchemy2.WKTElement(wkt_point, srid=4269)
        return await self.get_one_or_none(
            sqlalchemy.func.ST_Intersects(CatchmentModel.the_geom, point),
        )
