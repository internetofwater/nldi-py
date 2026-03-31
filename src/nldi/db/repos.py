# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Repositories for NLDI data access.

Thin wrappers around advanced-alchemy's async repository.
These are the boundary between the data model and the rest of the application.
"""

from advanced_alchemy.repository import SQLAlchemyAsyncRepository

from .models import CatchmentModel, CrawlerSourceModel, FeatureSourceModel, FlowlineModel


class CrawlerSourceRepository(SQLAlchemyAsyncRepository[CrawlerSourceModel]):
    """Repository for crawler source lookups."""

    model_type = CrawlerSourceModel
    id_attribute = "crawler_source_id"


class FeatureRepository(SQLAlchemyAsyncRepository[FeatureSourceModel]):
    """Repository for feature lookups."""

    model_type = FeatureSourceModel
    id_attribute = "identifier"


class FlowlineRepository(SQLAlchemyAsyncRepository[FlowlineModel]):
    """Repository for flowline lookups."""

    model_type = FlowlineModel
    id_attribute = "nhdplus_comid"


class CatchmentRepository(SQLAlchemyAsyncRepository[CatchmentModel]):
    """Repository for catchment lookups."""

    model_type = CatchmentModel
    id_attribute = "featureid"
