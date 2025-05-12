#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
""" """

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import geoalchemy2
import sqlalchemy
from advanced_alchemy.exceptions import NotFoundError
from advanced_alchemy.extensions.flask import FlaskServiceMixin
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from geomet import wkt
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.sql.expression import Select

from nldi.db.schemas.characteristics import (
    CharacteristicMetaData,
    DivergenceCharacteristics,
    LocalCharacteristics,
    TotalAccCharacteristics,
)
from nldi.db.schemas.nhdplus import CatchmentModel, FlowlineModel, FlowlineVAAModel
from nldi.db.schemas.nldi_data import CrawlerSourceModel, FeatureSourceModel

from .... import util
from ....db.schemas import struct_geojson
from .. import repos


class CharacteristicService(FlaskServiceMixin, SQLAlchemyAsyncRepositoryService[CharacteristicMetaData]):
    repository_type = repos.CharacteristicsDataRepository

    async def ListByType(self) -> list[CharacteristicMetaData]:
        flist, c = await svc.list_and_count(CharacteristicMetaData.characteristic_id.like("TOT%"))
        logging.debug(f"Found {c} TOT characteristics")
        return flist

# SELECT tac.comid, tac.characteristic_id, mdata.characteristic_description
# FROM characteristic_data.total_accumulated_characteristics as tac
# join characteristic_data.characteristic_metadata as mdata on  mdata.characteristic_id = tac.characteristic_id
# where tac.comid = 13293396
