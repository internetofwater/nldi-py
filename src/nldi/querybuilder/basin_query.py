#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
#
"""Building queries for basin lookups in the NLDI database."""

from typing import Any

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import aliased
from sqlalchemy.sql.selectable import Select

from .. import LOGGER, logger
from ..schemas.characteristic_data import CatchmentModel, FlowlineVAAModel



# def basin(comid: int, simplify: bool) -> Select:
#     """
#     Build a query to get the basin for a given comid.

#     :param comid: COMID for the feature
#     :type comid: int
#     :param simplify: Whether to simplify the geometry
#     :type simplify: bool
#     :return: sqlalchemy Select query
#     :rtype: sqlalchemy.sql.selectable.Select
#     """
#     fl_vaa = aliased(FlowlineVAAModel, name="fl_vaa")
#     nav = (
#         select([fl_vaa.comid, fl_vaa.hydroseq, fl_vaa.startflag])
#         .where(fl_vaa.comid == text(":comid"))
#         .cte("nav", recursive=True)
#     )

#     nav_basin = nav.union(
#         select([fl_vaa.comid, fl_vaa.hydroseq, fl_vaa.startflag]).where(
#             and_(
#                 (nav.c.startflag != 1),
#                 or_(
#                     (fl_vaa.dnhydroseq == nav.c.hydroseq),
#                     and_((fl_vaa.dnminorhyd != 0), (fl_vaa.dnminorhyd == nav.c.hydroseq)),
#                 ),
#             )
#         )
#     )

#     if simplify:
#         _geom = func.ST_AsGeoJSON(func.ST_Simplify(func.ST_Union(CatchmentModel.the_geom), 0.001), 9, 0).label(
#             "the_geom"
#         )
#     else:
#         _geom = func.ST_AsGeoJSON(func.ST_Union(CatchmentModel.the_geom), 9, 0).label("the_geom")

#     # Create the final query
#     query = select([_geom]).select_from(nav_basin).join(CatchmentModel, nav_basin.c.comid == CatchmentModel.featureid)

#     return query.params(comid=comid)


def basin_from_comid(comid: int, simplified: bool = True) -> Any:
    """
    Build a query to get the basin for a given comid.

    :param comid: the comid to look up
    :type comid: int
    :param simplified: Simplify the geometry or not
    :type simplified: bool
    :return: sqlalchemy Select query
    :rtype: sqlalchemy.sql.selectable.Select
    """
    nav = (
        select([FlowlineVAAModel.comid, FlowlineVAAModel.hydroseq, FlowlineVAAModel.startflag])
        .where(FlowlineVAAModel.comid == text(":comid"))
        .cte("nav", recursive=True)
    )

    x = aliased(FlowlineVAAModel, name="x")
    nav_basin = nav.union(
        select([x.comid, x.hydroseq, x.startflag]).where(
            and_(
                (nav.c.startflag != 1),
                or_((x.dnhydroseq == nav.c.hydroseq), and_((x.dnminorhyd != 0), (x.dnminorhyd == nav.c.hydroseq))),
            )
        )
    )

    if simplified:
        _geom = func.ST_AsGeoJSON(func.ST_Simplify(func.ST_Union(CatchmentModel.the_geom), 0.001), 9, 0).label(
            "the_geom"
        )
    else:
        _geom = func.ST_AsGeoJSON(func.ST_Union(CatchmentModel.the_geom), 9, 0).label("the_geom")

    # Create the final query
    query = select([_geom]).select_from(nav_basin).join(CatchmentModel, nav_basin.c.comid == CatchmentModel.featureid)

    return query.params(comid=comid)
