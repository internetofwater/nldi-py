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
from advanced_alchemy.extensions.flask import FlaskServiceMixin
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from geomet import wkt
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.sql.expression import Select

from nldi.db.schemas.nhdplus import CatchmentModel, FlowlineModel
from nldi.db.schemas.nldi_data import CrawlerSourceModel, FeatureSourceModel

from .... import util
from ....db.schemas import struct_geojson
from .. import repos


class CrawlerSourceService(FlaskServiceMixin, SQLAlchemyAsyncRepositoryService[CrawlerSourceModel]):
    repository_type = repos.CrawlerSourceRepository

    async def get_by_suffix(self, suffix: str) -> CrawlerSourceModel:
        _src = await self.get_one_or_none(sqlalchemy.func.lower(CrawlerSourceModel.source_suffix) == suffix.lower())
        if not _src:
            raise NotFoundError(f"No source found for {suffix=}")
        return _src

    async def suffix_exists(self, suffix: str) -> bool:
        if suffix == "comid":
            return True
        try:
            _src = await self.get_by_suffix(suffix)
        except NotFoundError:
            return False
        return True


async def crawler_source_svc(db_session: AsyncSession) -> AsyncGenerator[CrawlerSourceService, None]:
    """Provider function as part of the dependency-injection mechanism."""
    async with CrawlerSourceService.new(session=db_session) as service:
        yield service
