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
from collections.abc import Generator

import geoalchemy2
import sqlalchemy
from advanced_alchemy.exceptions import NotFoundError
from advanced_alchemy.extensions.flask import FlaskServiceMixin
from advanced_alchemy.service import SQLAlchemySyncRepositoryService
from geomet import wkt
from sqlalchemy.orm import Session

from sqlalchemy.sql.expression import Select

from nldi.db.schemas.nhdplus import CatchmentModel, FlowlineModel, FlowlineVAAModel
from nldi.db.schemas.nldi_data import CrawlerSourceModel, FeatureSourceModel

from .... import util
from ....db.schemas import struct_geojson
from .. import repos


class CatchmentService(FlaskServiceMixin, SQLAlchemySyncRepositoryService[CatchmentModel]):
    repository_type = repos.CatchmentRepository

    def get_by_wkt_point(self, coord_string: str) -> CatchmentModel:
        NAD83_SRID = 4269
        try:
            _ = wkt.loads(coord_string)  # using geomet just to validate the WKT.
            point = geoalchemy2.WKTElement(coord_string, srid=NAD83_SRID)
        except Exception as e:
            raise ValueError(f"Could not parse {coord_string} to valid geometry: {e}")
        catchment = self.get_by_geom(point)
        return catchment

    def get_by_geom(self, point: geoalchemy2.WKTElement | geoalchemy2.WKBElement) -> CatchmentModel:
        """
        Get a catchment feature by spatial intersect with the specified geometry.

        Note that a spatial selection may very well produce many results.  This method
        explicitly only returns one.  We produce the list internally, then just take
        the first item.  "first" is defined by the database .
        """
        _catchment =   self.get_one_or_none(sqlalchemy.func.ST_Intersects(CatchmentModel.the_geom, point))
        return _catchment

    def get_drainage_basin_by_comid(self, comid: int, simplified: bool) -> struct_geojson.Feature:
        """
        Compute upstream basin from a named comid.

        The comid matches a flowine

        :param comid: _description_
        :type comid: int
        :param simplified: _description_
        :type simplified: bool
        :raises KeyError: _description_
        :return: _description_
        :rtype: struct_geojson.Feature
        """
        nav = (
            sqlalchemy.select(FlowlineVAAModel.comid, FlowlineVAAModel.hydroseq, FlowlineVAAModel.startflag)
            .where(FlowlineVAAModel.comid == sqlalchemy.text(":comid"))
            .cte("nav", recursive=True)
        )

        # vaa = sqlalchemy.alias(FlowlineVAAModel, name="vaa")
        nav_basin = nav.union(
            sqlalchemy.select(FlowlineVAAModel.comid, FlowlineVAAModel.hydroseq, FlowlineVAAModel.startflag).where(
                sqlalchemy.and_(
                    (nav.c.startflag != 1),
                    sqlalchemy.or_(
                        (FlowlineVAAModel.dnhydroseq == nav.c.hydroseq),
                        sqlalchemy.and_(
                            (FlowlineVAAModel.dnminorhyd != 0), (FlowlineVAAModel.dnminorhyd == nav.c.hydroseq)
                        ),
                    ),
                )
            )
        )

        if simplified:
            _geom = sqlalchemy.func.ST_AsGeoJSON(
                sqlalchemy.func.ST_Simplify(sqlalchemy.func.ST_Union(CatchmentModel.the_geom), 0.001), 9, 0
            ).label("the_geom")
        else:
            _geom = sqlalchemy.func.ST_AsGeoJSON(sqlalchemy.func.ST_Union(CatchmentModel.the_geom), 9, 0).label(
                "the_geom"
            )

        # Create the final query
        query = (
            sqlalchemy.select(_geom)
            .select_from(nav_basin)
            .join(CatchmentModel, nav_basin.c.comid == CatchmentModel.featureid)
        )

        stmt = query.params(comid=comid)
        logging.debug(stmt.compile())
        hits = self.repository._execute(stmt)
        result = hits.fetchone()
        if result is None:
            raise KeyError(f"No such item: {comid}")
        return struct_geojson.Feature(properties=dict(), id=0, geometry=json.loads(result.the_geom))


def catchment_svc(db_session: Session) -> Generator[CatchmentModel, None, None]:
    """Provider function as part of the dependency-injection mechanism."""
    with CatchmentService.new(session=db_session) as service:
        yield service
