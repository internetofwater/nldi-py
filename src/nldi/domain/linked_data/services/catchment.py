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


class CatchmentService(SQLAlchemyAsyncRepositoryService[CatchmentModel]):
    repository_type = repos.CatchmentRepository

    async def get_by_wkt_point(self, coord_string: str) -> CatchmentModel:
        NAD83_SRID = 4269
        try:
            _ = wkt.loads(coord_string)  # using geomet just to validate the WKT.
            point = geoalchemy2.WKTElement(coord_string, srid=NAD83_SRID)
        except Exception as e:
            raise ValueError(f"Could not parse {coord_string} to valid geometry: {e}")
        catchment = await self.get_by_geom(point)
        return catchment

    async def get_by_geom(self, point: geoalchemy2.WKTElement | geoalchemy2.WKBElement) -> CatchmentModel:
        """
        Get a catchment feature by spatial intersect with the specified geometry.

        Note that a spatial selection may very well produce many results.  This method
        explicitly only returns one.  We produce the list internally, then just take
        the first item.  "first" is defined by the database .
        """
        _catchment = await self.get_one_or_none(sqlalchemy.func.ST_Intersects(CatchmentModel.the_geom, point))
        return _catchment


async def catchment_svc(db_session: AsyncSession) -> AsyncGenerator[CatchmentModel, None]:
    """Provider function as part of the dependency-injection mechanism."""
    async with CatchmentService.new(session=db_session) as service:
        yield service
