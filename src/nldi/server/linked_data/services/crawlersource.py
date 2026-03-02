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

from collections.abc import Generator

import sqlalchemy
from advanced_alchemy.exceptions import NotFoundError
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

# from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from nldi.db.schemas.nldi_data import CrawlerSourceModel

from .. import repos


class CrawlerSourceService(SQLAlchemyAsyncRepositoryService[CrawlerSourceModel]):
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


def crawler_source_svc(db_session: AsyncSession) -> Generator[CrawlerSourceService, None, None]:
    """Provider function as part of the dependency-injection mechanism."""
    with CrawlerSourceService.new(session=db_session) as service:
        yield service
