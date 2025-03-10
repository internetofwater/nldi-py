#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""
Base Repositories for NLDI data retrieval.

This is a "repository" in the sense of the "repository pattern", one of the
design patterns in the Gang Of Four book. These repos are an abstraction to
hide a lot of the detail for fetching items from the underlying data store.
The repository exposes CRUD (and CRUD-like) methods to the caller.
"""

from advanced_alchemy.repository import SQLAlchemyAsyncRepository

from nldi.db.schemas import struct_geojson
from nldi.db.schemas.nhdplus import CatchmentModel, FlowlineModel
from nldi.db.schemas.nldi_data import CrawlerSourceModel, FeatureSourceModel


class CrawlerSourceRepository(SQLAlchemyAsyncRepository[CrawlerSourceModel]):
    model_type = CrawlerSourceModel
    id_attribute = "crawler_source_id"

    def __init__(self, **kwargs):
        """
        For unknown reason, I am not able to get `order_by` to stick as an
        execution_option. So I am resorting to this ugly hack.
        """  # noqa: D205
        kwargs["order_by"] = [("crawler_source_id", "desc")]
        return super().__init__(**kwargs)


class FlowlineRepository(SQLAlchemyAsyncRepository[FlowlineModel]):
    model_type = FlowlineModel
    id_attribute = "nhdplus_comid"


class CatchmentRepository(SQLAlchemyAsyncRepository[CatchmentModel]):
    model_type = CatchmentModel
    id_attribute = "featureid"


class FeatureRepository(SQLAlchemyAsyncRepository[FeatureSourceModel]):
    model_type = FeatureSourceModel
    id_attribute = "identifier"
