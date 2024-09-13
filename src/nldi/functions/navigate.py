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

"""Module containing the models for NLDI Navigation"""

from enum import Enum
from typing import Any

from sqlalchemy import and_, case, func, or_, select, text
from sqlalchemy.orm import aliased

from nldi.schemas.nhdplus import FlowlineModel, FlowlineVAAModel

from .. import LOGGER

COASTAL_FCODE = 56600


class NavigationModes(str, Enum):
    DM = "DM"  # Downstream navigation on the Main channel
    DD = "DD"  # Downstream navigation with Diversions
    UM = "UM"  # Upstream navigation on the Main channel
    UT = "UT"  # Upstream navigation with Tributaries
    # PP = "PP"  # Point-to-Point navigation ; the stopComid query parameter is required and must be downstream of the comid.


def trim_navigation(nav_mode: str, comid: int, trim_tolerance: float, measure: float):
    scaled_measure = 1 - ((measure - FlowlineModel.fmeasure) / (FlowlineModel.tmeasure - FlowlineModel.fmeasure))

    if nav_mode in [NavigationModes.DD, NavigationModes.DM]:
        geom = func.ST_AsGeoJSON(func.ST_LineSubstring(FlowlineModel.shape, scaled_measure, 1), 9, 0)
    elif nav_mode in [NavigationModes.UT, NavigationModes.UM]:
        geom = func.ST_AsGeoJSON(func.ST_LineSubstring(FlowlineModel.shape, 0, scaled_measure), 9, 0)

    if 100 - measure >= trim_tolerance:
        LOGGER.debug("Forming trim query")
        nav_trim = case(
            (FlowlineModel.nhdplus_comid == text(":comid"), geom), else_=func.ST_AsGeoJSON(FlowlineModel.shape, 9, 0)
        )

        query = select([FlowlineModel.nhdplus_comid.label("comid"), nav_trim.label("geom")])
    else:
        query = select(
            [FlowlineModel.nhdplus_comid.label("comid"), func.ST_AsGeoJSON(FlowlineModel.shape, 9, 0).label("geom")]
        )

    return query.params(comid=comid)


def get_navigation(nav_mode: str, comid: int, distance: float = None, coastal_fcode: int = COASTAL_FCODE) -> Any:
    LOGGER.debug(f"Doing navigation for {comid} with mode {nav_mode}")
    if nav_mode == NavigationModes.DM:
        return navigate_dm(comid, distance, coastal_fcode)
    elif nav_mode == NavigationModes.DD:
        return navigate_dd(comid, distance, coastal_fcode)
    elif nav_mode == NavigationModes.UM:
        return navigate_um(comid, distance, coastal_fcode)
    elif nav_mode == NavigationModes.UT:
        return navigate_ut(comid, distance, coastal_fcode)


def navigate_dm(comid, distance, coastal_fcode):
    nav = (
        select(
            [
                FlowlineVAAModel.comid,
                FlowlineVAAModel.terminalpathid,
                FlowlineVAAModel.dnhydroseq,
                FlowlineVAAModel.fcode,
                (FlowlineVAAModel.pathlength + FlowlineVAAModel.lengthkm - text(":distance")).label("stoplength"),  # noqa
            ]
        )
        .where(FlowlineVAAModel.comid == text(":comid"))
        .cte("nav", recursive=True)
    )

    x = aliased(FlowlineVAAModel, name="x")
    nav_dm = nav.union(
        select([x.comid, x.terminalpathid, x.dnhydroseq, x.fcode, nav.c.stoplength]).where(
            and_(
                (x.hydroseq == nav.c.dnhydroseq),
                (x.terminalpathid == nav.c.terminalpathid),
                (x.fcode != text(":coastal_fcode")),
                (x.pathlength + x.lengthkm >= nav.c.stoplength),
            )
        )
    )

    # Create the final query
    query = select([nav_dm.c.comid]).select_from(nav_dm)

    return query.params(distance=distance, comid=comid, coastal_fcode=coastal_fcode)


def navigate_dd(comid, distance, coastal_fcode):
    nav = (
        select(
            [
                FlowlineVAAModel.comid,
                FlowlineVAAModel.dnhydroseq,
                FlowlineVAAModel.dnminorhyd,
                FlowlineVAAModel.fcode,
                (FlowlineVAAModel.pathlength + FlowlineVAAModel.lengthkm - text(":distance")).label("stoplength"),  # noqa
                FlowlineVAAModel.terminalflag,
            ]
        )
        .where(FlowlineVAAModel.comid == text(":comid"))
        .cte("nav", recursive=True)
    )

    x = aliased(FlowlineVAAModel, name="x")
    nav_dd = nav.union(
        select([x.comid, x.dnhydroseq, x.dnminorhyd, x.fcode, nav.c.stoplength, x.terminalflag]).where(
            and_(
                (x.fcode != text(":coastal_fcode")),
                (nav.c.terminalflag != 1),
                (x.pathlength + x.lengthkm >= nav.c.stoplength),
                or_(x.hydroseq == nav.c.dnhydroseq, and_(nav.c.dnminorhyd != 0, x.hydroseq == nav.c.dnminorhyd)),
            )
        )
    )
    # Create the final query
    query = select([nav_dd.c.comid]).select_from(nav_dd)

    return query.params(distance=distance, comid=comid, coastal_fcode=coastal_fcode)


def navigate_um(comid, distance, coastal_fcode):
    nav = (
        select(
            [
                FlowlineVAAModel.comid,
                FlowlineVAAModel.levelpathid,
                FlowlineVAAModel.uphydroseq,
                FlowlineVAAModel.fcode,
                (FlowlineVAAModel.pathlength + text(":distance")).label("stoplength"),  # noqa
            ]
        )
        .where(FlowlineVAAModel.comid == text(":comid"))
        .cte("nav", recursive=True)
    )

    x = aliased(FlowlineVAAModel, name="x")
    nav_um = nav.union(
        select([x.comid, x.levelpathid, x.uphydroseq, x.fcode, nav.c.stoplength]).where(
            and_(
                (x.hydroseq == nav.c.uphydroseq),
                (x.levelpathid == nav.c.levelpathid),
                (x.fcode != text(":coastal_fcode")),
                (x.pathlength <= nav.c.stoplength),
            )
        )
    )

    # Create the final query
    query = select([nav_um.c.comid]).select_from(nav_um)

    return query.params(distance=distance, comid=comid, coastal_fcode=coastal_fcode)


def navigate_ut(comid, distance=0, coastal_fcode=COASTAL_FCODE):
    nav = (
        select(
            [
                FlowlineVAAModel.comid,
                FlowlineVAAModel.hydroseq,
                FlowlineVAAModel.startflag,
                FlowlineVAAModel.fcode,
                (FlowlineVAAModel.pathlength + text(":distance")).label("stoplength"),  # noqa
            ]
        )
        .where(FlowlineVAAModel.comid == text(":comid"))
        .cte("nav", recursive=True)
    )

    x = aliased(FlowlineVAAModel, name="x")
    nav_ut = nav.union(
        select([x.comid, x.hydroseq, x.startflag, x.fcode, nav.c.stoplength]).where(
            and_(
                (x.fcode != text(":coastal_fcode")),
                (nav.c.startflag != 1),
                (x.pathlength <= nav.c.stoplength),
                or_(x.dnhydroseq == nav.c.hydroseq, and_(x.dnminorhyd != 0, x.dnminorhyd == nav.c.hydroseq)),
            )
        )
    )
    # Create the final query
    query = select([nav_ut.c.comid]).select_from(nav_ut)

    return query.params(distance=distance, comid=comid, coastal_fcode=coastal_fcode)
