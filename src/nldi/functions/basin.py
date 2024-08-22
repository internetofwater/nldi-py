# =================================================================
#
# Author: Benjamin Webb <bwebb@lincolninst.edu>
#
# Copyright (c) 2023 Benjamin Webb
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# =================================================================

"""Module containing the models for NLDI Basin Lookup"""

from typing import Any

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import aliased
from sqlalchemy.sql.selectable import Select

from .. import LOGGER
from ..schemas.characteristic_data import CatchmentModel, FlowlineVAAModel


def basin_query(comid: int, simplify: bool) -> Select:
    """
    Build a query to get the basin for a given comid

    :param comid: COMID for the feature
    :type comid: int
    :param simplify: Whether to simplify the geometry
    :type simplify: bool
    :return: sqlalchemy Select query
    :rtype: sqlalchemy.sql.selectable.Select
    """
    fl_vaa = aliased(FlowlineVAAModel, name="fl_vaa")
    nav = (
        select([fl_vaa.comid, fl_vaa.hydroseq, fl_vaa.startflag])
        .where(fl_vaa.comid == text(":comid"))
        .cte("nav", recursive=True)
    )

    nav_basin = nav.union(
        select([fl_vaa.comid, fl_vaa.hydroseq, fl_vaa.startflag]).where(
            and_(
                (nav.c.startflag != 1),
                or_((fl_vaa.dnhydroseq == nav.c.hydroseq), and_((fl_vaa.dnminorhyd != 0), (fl_vaa.dnminorhyd == nav.c.hydroseq))),
            )
        )
    )

    if simplify:
        _geom = func.ST_AsGeoJSON(func.ST_Simplify(func.ST_Union(CatchmentModel.the_geom), 0.001), 9, 0).label(
            "the_geom"
        )
    else:
        _geom = func.ST_AsGeoJSON(func.ST_Union(CatchmentModel.the_geom), 9, 0).label("the_geom")

    # Create the final query
    query = select([_geom]).select_from(nav_basin).join(CatchmentModel, nav_basin.c.comid == CatchmentModel.featureid)

    return query.params(comid=comid)
    

def get_basin(comid: int, simplified: bool) -> Any:
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
