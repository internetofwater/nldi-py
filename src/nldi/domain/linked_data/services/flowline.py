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
import sqlalchemy
from advanced_alchemy.exceptions import NotFoundError
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from geomet import wkt
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.sql.expression import Select

from nldi.db.schemas.nhdplus import CatchmentModel, FlowlineModel
from nldi.db.schemas.nldi_data import CrawlerSourceModel, FeatureSourceModel

from .... import util
from ....db.schemas import struct_geojson
from .. import repos


class FlowlineService(SQLAlchemyAsyncRepositoryService[FlowlineModel]):
    repository_type = repos.FlowlineRepository

    async def get(self, id: str | int, *args, **kwargs) -> FlowlineModel:
        _id = int(id)
        return await super().get(_id, *args, **kwargs)

    async def get_feature(self, comid: str | int, xtra_props: dict[str, str] | None = None) -> struct_geojson.Feature:
        _feature = await self.get(comid)

        _result = _feature.as_feature(
            rename_fields={
                "permanent_identifier": "identifier",
                "nhdplus_comid": "comid",
            },
            xtra_props=xtra_props,
        )
        _result.id = _feature.nhdplus_comid
        return _result

    async def features_from_nav_query(self, nav_query: Select) -> list[struct_geojson.Feature]:
        subq = nav_query.subquery()
        stmt = sqlalchemy.select(FlowlineModel).join(subq, FlowlineModel.nhdplus_comid == subq.c.comid)
        hits = await self.repository._execute(stmt)
        r = hits.fetchall()
        return [
            f[0].as_feature(excl_props=["objectid", "permanent_identifier", "fmeasure", "tmeasure", "reachcode"])
            for f in r
        ]

    async def trimed_features_from_nav_query(self, nav_query: Select, trim_query: Select) -> list:
        nav_subq = nav_query.subquery()
        trim_subq = trim_query.subquery()
        stmt = (
            sqlalchemy.select(FlowlineModel, trim_subq.c.trimmed_geojson)
            .join(nav_subq, FlowlineModel.nhdplus_comid == nav_subq.c.comid)
            .join(trim_subq, FlowlineModel.nhdplus_comid == trim_subq.c.comid)
        )
        r = []
        hits = await self.repository._execute(stmt)
        for f, g in hits.fetchall():
            _tmp = f.as_feature(excl_props=["objectid", "permanent_identifier", "fmeasure", "tmeasure", "reachcode"])
            _tmp.geometry = json.loads(g)  # Overwrite geom with trimmed geom
            r.append(_tmp)
        return r


async def flowline_svc(db_session: AsyncSession) -> AsyncGenerator[FlowlineService, None]:
    """Provider function as part of the dependency-injection mechanism."""
    async with FlowlineService.new(session=db_session) as service:
        yield service
