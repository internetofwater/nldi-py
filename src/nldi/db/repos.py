# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Repositories for NLDI data access.

Thin wrappers around advanced-alchemy's async repository.
These are the boundary between the data model and the rest of the application.
"""

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


class FlowlineRepository(SQLAlchemyAsyncRepository[FlowlineModel]):
    """Repository for flowline lookups."""

    model_type = FlowlineModel
    id_attribute = "nhdplus_comid"


class CatchmentRepository(SQLAlchemyAsyncRepository[CatchmentModel]):
    """Repository for catchment lookups."""

    model_type = CatchmentModel
    id_attribute = "featureid"
