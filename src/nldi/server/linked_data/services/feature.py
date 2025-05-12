#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
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
from collections.abc import AsyncGenerator

import geoalchemy2
import msgspec
import sqlalchemy
from advanced_alchemy.exceptions import NotFoundError
from advanced_alchemy.extensions.flask import FlaskServiceMixin, filters
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from geomet import wkt
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import joinedload, load_only, selectinload
from sqlalchemy.sql.expression import Select

from nldi.db.schemas.nhdplus import CatchmentModel, FlowlineModel
from nldi.db.schemas.nldi_data import CrawlerSourceModel, FeatureSourceModel

from .... import util
from ....db.schemas import struct_geojson
from .. import repos


class FeatureService(FlaskServiceMixin, SQLAlchemyAsyncRepositoryService[FeatureSourceModel]):
    repository_type = repos.FeatureRepository

    async def feature_lookup(self, source_suffix: str, identifier: str) -> FeatureSourceModel:
        _f = await self.repository.get_one_or_none(
            sqlalchemy.func.lower(CrawlerSourceModel.source_suffix) == source_suffix.lower(),
            FeatureSourceModel.identifier == identifier,
            statement=sqlalchemy.select(FeatureSourceModel).join(
                CrawlerSourceModel, FeatureSourceModel.crawler_source_id == CrawlerSourceModel.crawler_source_id
            ),
        )
        if _f is None:
            raise NotFoundError(f"Feature {identifier} from source {source_suffix} not found.")
        return _f

    async def featurecount(self, source_suffix: str) -> int:
        _count = await self.count(
            sqlalchemy.func.lower(CrawlerSourceModel.source_suffix) == source_suffix.lower(),
            statement=sqlalchemy.select(FeatureSourceModel.identifier).join(
                CrawlerSourceModel, FeatureSourceModel.crawler_source_id == CrawlerSourceModel.crawler_source_id
            ),
        )
        return _count

    async def list_by_src(self, source_suffix: str, offset: int = 0, limit: int = 1000) -> list[FeatureSourceModel]:
        _l = await self.repository.list(
            sqlalchemy.func.lower(CrawlerSourceModel.source_suffix) == source_suffix.lower(),
            filters.LimitOffset(limit=limit, offset=offset),
            statement=sqlalchemy.select(FeatureSourceModel).join(
                CrawlerSourceModel, FeatureSourceModel.crawler_source_id == CrawlerSourceModel.crawler_source_id
            ),
        )
        return list(_l)

    async def iter_by_src(
        self, source_suffix: str, base_url: str = "", offset: int = 0, limit: int = 1000
    ) -> AsyncGenerator[bytes, None]:
        """Provides a streaming response for the feature collection."""
        stmt = (
            sqlalchemy.select(FeatureSourceModel)
            .where(sqlalchemy.func.lower(CrawlerSourceModel.source_suffix) == source_suffix.lower())
            .execution_options(yield_per=5)
            .join(CrawlerSourceModel, FeatureSourceModel.crawler_source_id == CrawlerSourceModel.crawler_source_id)
            .offset(offset)
            .limit(limit)
        )

        query_result = await self.repository.session.stream(stmt)
        while f := await query_result.fetchone():
            nav_url = util.url_join(base_url, "linked-data", source_suffix, f[0].identifier, "navigation")
            yield (
                msgspec.to_builtins(
                    f[0].as_feature(excl_props=["crawler_source_id"], xtra_props={"navigation": nav_url})
                )
            )

    async def features_from_nav_query(self, source_suffix: str, nav_query: Select) -> list[FeatureSourceModel]:
        subq = nav_query.subquery()
        stmt = (
            sqlalchemy.select(FeatureSourceModel)
            .where(sqlalchemy.func.lower(CrawlerSourceModel.source_suffix) == source_suffix.lower())
            .join(CrawlerSourceModel, CrawlerSourceModel.crawler_source_id == FeatureSourceModel.crawler_source_id)
            .join(subq, FeatureSourceModel.comid == subq.c.comid)
        )
        hits = await self.repository._execute(stmt)
        r = hits.fetchall()
        return [f[0].as_feature(excl_props=["reachcode"]) for f in r]


async def feature_svc(db_session: AsyncSession) -> AsyncGenerator[FeatureSourceModel, None]:
    """Provider function as part of the dependency-injection mechanism."""
    async with FeatureService.new(session=db_session) as service:
        yield service
