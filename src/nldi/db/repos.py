# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Repositories for NLDI data access.

Thin wrappers around plain SQLAlchemy async sessions.
These are the boundary between the data model and the rest of the application.
"""

import geoalchemy2
import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from .models import CatchmentModel, CrawlerSourceModel, FeatureSourceModel, FlowlineModel


class AsyncRepository:
    """Minimal async repository base with list and get_one_or_none."""

    model_type: type
    _cancel_pid: int | None = None

    def __init__(self, session: AsyncSession):
        """Initialize with an async session."""
        self.session = session

    async def cancel_running_query(self) -> None:
        """Cancel the in-flight query via pg_cancel_backend, if any.

        Uses pg_cancel_backend rather than closing the connection directly.
        For pure SQL queries (navigation CTEs), pg_cancel_backend responds in
        milliseconds and allows the connection to recover and be returned to
        the pool for reuse. Closing the connection would also work but discards
        it, forcing a new connection on next checkout — expensive under load.

        CatchmentRepository overrides this with a direct connection close
        because GEOS geometry operations (ST_Union) ignore pg_cancel_backend
        for minutes and require OS-level termination.
        """
        pid = self._cancel_pid
        if not pid:
            return
        import logging
        logging.getLogger(__name__).debug("Cancelling query on backend PID %s", pid)
        from . import get_cancel_engine

        async with get_cancel_engine().connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT pg_cancel_backend(:pid)"), {"pid": pid})
            await conn.commit()

    async def list(self, statement: sqlalchemy.sql.Select | None = None) -> list:
        """Execute a SELECT and return all model instances."""
        stmt = statement if statement is not None else sqlalchemy.select(self.model_type)
        result = await self.session.execute(stmt)
        return list(result.scalars())

    async def get_one_or_none(self, *filters: sqlalchemy.ColumnElement, statement: sqlalchemy.sql.Select | None = None):
        """Execute a filtered SELECT and return one result or None."""
        stmt = statement if statement is not None else sqlalchemy.select(self.model_type)
        for f in filters:
            stmt = stmt.where(f)
        result = await self.session.execute(stmt)
        return result.scalars().one_or_none()


class CrawlerSourceRepository(AsyncRepository):
    """Repository for crawler source lookups."""

    model_type = CrawlerSourceModel

    async def get_by_suffix(self, suffix: str) -> CrawlerSourceModel | None:
        """Look up a source by suffix, case-insensitive."""
        return await self.get_one_or_none(
            sqlalchemy.func.lower(CrawlerSourceModel.source_suffix) == suffix.lower(),
        )


class FeatureRepository(AsyncRepository):
    """Repository for feature lookups."""

    model_type = FeatureSourceModel

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
        self._cancel_pid = await self.session.scalar(sqlalchemy.text("SELECT pg_backend_pid()"))
        try:
            subq = nav_query.subquery()
            stmt = (
                sqlalchemy.select(FeatureSourceModel)
                .join(CrawlerSourceModel, FeatureSourceModel.crawler_source_id == CrawlerSourceModel.crawler_source_id)
                .join(subq, FeatureSourceModel.comid == subq.c.comid)
                .where(sqlalchemy.func.lower(CrawlerSourceModel.source_suffix) == data_source.lower())
                .options(sqlalchemy.orm.joinedload(FeatureSourceModel.mainstem_lookup))
            )
            return list(await self.list(statement=stmt))
        finally:
            self._cancel_pid = None


class FlowlineRepository(AsyncRepository):
    """Repository for flowline lookups."""

    model_type = FlowlineModel

    async def get_by_comid(self, comid: int) -> FlowlineModel | None:
        """Look up a flowline by comid."""
        return await self.get_one_or_none(FlowlineModel.nhdplus_comid == comid)

    async def list_all(self, limit: int = 0, offset: int = 0) -> list[FlowlineModel]:
        """List flowlines with optional pagination."""
        stmt = sqlalchemy.select(FlowlineModel).order_by(FlowlineModel.nhdplus_comid).offset(offset)
        if limit > 0:
            stmt = stmt.limit(limit)
        return list(await self.list(statement=stmt))

    async def from_nav_query(self, nav_query: sqlalchemy.sql.Select) -> list[FlowlineModel]:
        """Execute a navigation CTE and join to flowlines."""
        self._cancel_pid = await self.session.scalar(sqlalchemy.text("SELECT pg_backend_pid()"))
        try:
            subq = nav_query.subquery()
            stmt = sqlalchemy.select(FlowlineModel).join(subq, FlowlineModel.nhdplus_comid == subq.c.comid)
            return list(await self.list(statement=stmt))
        finally:
            self._cancel_pid = None

    async def from_trimmed_nav_query(
        self, nav_query: sqlalchemy.sql.Select, trim_query: sqlalchemy.sql.Select
    ) -> list:  # list of (FlowlineModel, geojson_str) tuples
        """Execute navigation + trim queries, return flowlines with trimmed geometry."""
        self._cancel_pid = await self.session.scalar(sqlalchemy.text("SELECT pg_backend_pid()"))
        try:
            nav_subq = nav_query.subquery()
            trim_subq = trim_query.subquery()
            stmt = (
                sqlalchemy.select(FlowlineModel, trim_subq.c.trimmed_geojson)
                .join(nav_subq, FlowlineModel.nhdplus_comid == nav_subq.c.comid)
                .join(trim_subq, FlowlineModel.nhdplus_comid == trim_subq.c.comid)
            )
            result = await self.session.execute(stmt)
            return list(result)
        finally:
            self._cancel_pid = None

    async def get_measure_and_reachcode(self, comid: int, wkt_point: str) -> tuple[float | None, str | None]:
        """Compute measure and reachcode for a point on a flowline."""
        measure_expr = (
            FlowlineModel.fmeasure
            + (
                1
                - sqlalchemy.func.ST_LineLocatePoint(
                    FlowlineModel.shape, sqlalchemy.func.ST_GeomFromText(wkt_point, 4269)
                )
            )
            * (FlowlineModel.tmeasure - FlowlineModel.fmeasure)
        ).label("measure")
        stmt = sqlalchemy.select(measure_expr, FlowlineModel.reachcode).where(FlowlineModel.nhdplus_comid == comid)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        if not row:
            return None, None
        return float(row[0]) if row[0] is not None else None, row[1]

    async def feat_get_point_along_flowline(self, feature_id: str, feature_source: str) -> tuple[float, float] | None:
        """Interpolate a point along the flowline using the feature's measure.

        Returns (lon, lat) or None if the feature has no measure.

        Should compile to::

            SELECT ST_X(ST_LineInterpolatePoint(shape, scaled)), ST_Y(...)
            FROM nhdplus.nhdflowline_np21
            JOIN nldi_data.feature ON feature.comid = nhdflowline_np21.nhdplus_comid
              AND feature.identifier = :feature_id
            JOIN nldi_data.crawler_source ON lower(source_suffix) = :feature_source
              AND feature.crawler_source_id = crawler_source.crawler_source_id
        """
        scaled = 1 - (
            (FeatureSourceModel.measure - FlowlineModel.fmeasure) / (FlowlineModel.tmeasure - FlowlineModel.fmeasure)
        )
        point = sqlalchemy.func.ST_LineInterpolatePoint(FlowlineModel.shape, scaled)
        stmt = (
            sqlalchemy.select(
                sqlalchemy.func.ST_X(point).label("lon"),
                sqlalchemy.func.ST_Y(point).label("lat"),
            )
            .join(
                FeatureSourceModel,
                sqlalchemy.and_(
                    FeatureSourceModel.comid == FlowlineModel.nhdplus_comid,
                    FeatureSourceModel.identifier == sqlalchemy.bindparam("feature_id"),
                ),
            )
            .join(
                CrawlerSourceModel,
                sqlalchemy.and_(
                    sqlalchemy.func.lower(CrawlerSourceModel.source_suffix) == sqlalchemy.bindparam("feature_source"),
                    FeatureSourceModel.crawler_source_id == CrawlerSourceModel.crawler_source_id,
                ),
            )
            .params(feature_id=feature_id, feature_source=feature_source.lower())
        )
        result = await self.session.execute(stmt)
        row = result.fetchone()
        if not row or None in row:
            return None
        return (float(row[0]), float(row[1]))

    async def feat_get_distance_from_flowline(self, feature_id: str, feature_source: str) -> float | None:
        """Compute distance (meters) between a feature and its flowline.

        Should compile to::

            SELECT ST_Distance(feature.location, nhdflowline_np21.shape, false)
            FROM nhdplus.nhdflowline_np21
            JOIN nldi_data.feature ON feature.comid = nhdflowline_np21.nhdplus_comid
              AND feature.identifier = :feature_id
            JOIN nldi_data.crawler_source ON lower(source_suffix) = :feature_source
              AND feature.crawler_source_id = crawler_source.crawler_source_id
        """
        shapes = (
            sqlalchemy.select(
                FlowlineModel.shape.label("shape"),
                FeatureSourceModel.location.label("location"),
            )
            .join(
                FeatureSourceModel,
                sqlalchemy.and_(
                    FeatureSourceModel.comid == FlowlineModel.nhdplus_comid,
                    FeatureSourceModel.identifier == sqlalchemy.bindparam("feature_id"),
                ),
            )
            .join(
                CrawlerSourceModel,
                sqlalchemy.and_(
                    sqlalchemy.func.lower(CrawlerSourceModel.source_suffix) == sqlalchemy.bindparam("feature_source"),
                    FeatureSourceModel.crawler_source_id == CrawlerSourceModel.crawler_source_id,
                ),
            )
            .alias("shapes")
        )
        stmt = sqlalchemy.select(sqlalchemy.func.ST_Distance(shapes.c.location, shapes.c.shape, False)).params(
            feature_id=feature_id, feature_source=feature_source.lower()
        )
        result = await self.session.execute(stmt)
        dist = result.scalar()
        return float(dist) if dist is not None else None

    async def feat_get_nearest_point_on_flowline(
        self, feature_id: str, feature_source: str
    ) -> tuple[float, float] | None:
        """Find the closest point on the flowline to the feature location.

        Should compile to::

            SELECT ST_X(ST_ClosestPoint(shape, location)), ST_Y(...)
            FROM nhdplus.nhdflowline_np21
            JOIN nldi_data.feature ON feature.comid = nhdflowline_np21.nhdplus_comid
              AND feature.identifier = :feature_id
            JOIN nldi_data.crawler_source ON lower(source_suffix) = :feature_source
              AND feature.crawler_source_id = crawler_source.crawler_source_id
        """
        shapes = (
            sqlalchemy.select(
                FlowlineModel.shape.label("shape"),
                FeatureSourceModel.location.label("location"),
            )
            .join(
                FeatureSourceModel,
                sqlalchemy.and_(
                    FeatureSourceModel.comid == FlowlineModel.nhdplus_comid,
                    FeatureSourceModel.identifier == sqlalchemy.bindparam("feature_id"),
                ),
            )
            .join(
                CrawlerSourceModel,
                sqlalchemy.and_(
                    sqlalchemy.func.lower(CrawlerSourceModel.source_suffix) == sqlalchemy.bindparam("feature_source"),
                    FeatureSourceModel.crawler_source_id == CrawlerSourceModel.crawler_source_id,
                ),
            )
            .alias("shapes")
        )
        point = sqlalchemy.select(
            sqlalchemy.func.ST_ClosestPoint(shapes.c.shape, shapes.c.location).label("point")
        ).alias("point")
        stmt = sqlalchemy.select(
            sqlalchemy.func.ST_X(point.c.point).label("lon"),
            sqlalchemy.func.ST_Y(point.c.point).label("lat"),
        ).params(feature_id=feature_id, feature_source=feature_source.lower())
        result = await self.session.execute(stmt)
        row = result.fetchone()
        if not row or None in row:
            return None
        return (float(row[0]), float(row[1]))


class CatchmentRepository(AsyncRepository):
    """Repository for catchment lookups."""

    model_type = CatchmentModel

    async def cancel_running_query(self) -> None:
        """Close the underlying connection to force-kill the basin query.

        Overrides the base pg_cancel_backend approach because GEOS geometry
        operations (ST_Union, ST_Simplify) ignore Postgres interrupt signals
        for minutes — making pg_cancel_backend ineffective for basin queries.

        Closing the TCP connection causes Postgres to detect a lost client and
        kill the backend at the OS level immediately. This is the same mechanism
        the Java implementation relies on: a thread interrupt closes the JDBC
        socket, which Postgres detects and uses to terminate the backend.

        The connection is discarded rather than returned to the pool, but that
        is acceptable — a new connection is cheaper than holding a stuck one.
        """
        if not self._cancel_pid:
            return
        import logging
        logger = logging.getLogger(__name__)
        logger.debug("Closing connection for basin PID %s", self._cancel_pid)
        try:
            conn = await self.session.connection()
            raw = await conn.get_raw_connection()
            await raw.driver_connection.close()
        except Exception as e:
            logger.warning("Failed to close basin connection: %s", e)

    async def get_by_point(self, wkt_point: str) -> CatchmentModel | None:
        """Find a catchment by spatial intersection with a WKT point."""
        point = geoalchemy2.WKTElement(wkt_point, srid=4269)
        return await self.get_one_or_none(
            sqlalchemy.func.ST_Intersects(CatchmentModel.the_geom, point),
        )

    async def get_drainage_basin(self, basin_nav_query: sqlalchemy.sql.Select, simplified: bool = True) -> str | None:
        """Aggregate upstream catchment polygons into a basin geometry.

        Returns GeoJSON string of the unioned polygon, optionally simplified.
        """
        self._cancel_pid = await self.session.scalar(sqlalchemy.text("SELECT pg_backend_pid()"))
        try:
            subq = basin_nav_query.subquery()
            if simplified:
                geom = sqlalchemy.func.ST_AsGeoJSON(
                    sqlalchemy.func.ST_Simplify(sqlalchemy.func.ST_Union(CatchmentModel.the_geom), 0.001), 9, 0
                )
            else:
                geom = sqlalchemy.func.ST_AsGeoJSON(sqlalchemy.func.ST_Union(CatchmentModel.the_geom), 9, 0)

            stmt = (
                sqlalchemy.select(geom.label("shape"))
                .select_from(subq)
                .join(CatchmentModel, subq.c.comid == CatchmentModel.featureid)
            )
            result = await self.session.execute(stmt)
            row = result.fetchone()
            if not row or not row[0]:
                return None
            return str(row[0])
        finally:
            self._cancel_pid = None
