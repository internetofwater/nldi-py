#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
#
"""navigation queries for the NLDI database"""

from enum import StrEnum
from typing import Any

import sqlalchemy
from sqlalchemy import and_, case, func, or_, select, text
from sqlalchemy.orm import aliased

from .. import LOGGER
from ..schemas.nhdplus import FlowlineModel, FlowlineVAAModel

COASTAL_FCODE = 56600


class NavigationModes(StrEnum):  ## StrEnum requires python 3.11 or better
    """Modes for the NLDI Navigation."""

    DM = "DM"
    DD = "DD"
    UM = "UM"
    UT = "UT"
    # PP = "PP"


## Convenience dictionary to map the mode enum to a human-readable description
NavModesDesc = {
    NavigationModes.DM: "Downstream navigation on the Main channel",
    NavigationModes.DD: "Downstream navigation with Diversions",
    NavigationModes.UM: "Upstream navigation on the Main channel",
    NavigationModes.UT: "Upstream navigation with Tributaries",
    # NavigationModes.PP:  # Point-to-Point navigation ; the stopComid query parameter is required and must be downstream of the comid.
}


def navmode_description(nav_mode: NavigationModes) -> str:
    return NavModesDesc[nav_mode]


def navigation(
    nav_mode: NavigationModes,
    comid: int,
    distance: float | None = None,
    coastal_fcode: int = COASTAL_FCODE,
) -> sqlalchemy.sql.selectable.Select:
    """
    Create a query for navigation.

    The navigation query logic depends on the navigation mode.  The navigation modes are defined
    in the NavigationModes enum.  The navigation query is created by calling the appropriate
    navigation function based on the navigation mode.  The navigation function is selected from
    the _modes dictionary, which is hard-coded in this module.

    This function's sole purpose is to proxy the call to the appropriate navigation function, based
    on the value of the ``nav_mode`` parameter.
    """
    _modes = {
        NavigationModes.DM: navigate_dm,
        NavigationModes.DD: navigate_dd,
        NavigationModes.UM: navigate_um,
        NavigationModes.UT: navigate_ut,
    }
    if nav_mode not in _modes:
        LOGGER.error(f"Invalid navigation mode: {nav_mode}")
        raise ValueError(f"Invalid navigation mode: {nav_mode}")
    else:
        func = _modes[nav_mode]
    return func(comid, distance, coastal_fcode)


def navigate_dm(
    comid: int,
    distance: float | None,
    coastal_fcode: int,
) -> sqlalchemy.sql.selectable.Select:
    """
    Create a navigation query for the DM mode.

    The DM mode is the Downstream navigation on the Main channel.
    """
    LOGGER.debug(f"Creating navigation query for DM mode: {comid=}, {distance=}, {coastal_fcode=}")
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


def navigate_dd(
    comid: int,
    distance: float | None,
    coastal_fcode: int,
) -> sqlalchemy.sql.selectable.Select:
    LOGGER.debug(f"Creating navigation query for DD mode: {comid=}, {distance=}, {coastal_fcode=}")
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

    vaa = aliased(FlowlineVAAModel, name="vaa")
    nav_dd = nav.union(
        select([vaa.comid, vaa.dnhydroseq, vaa.dnminorhyd, vaa.fcode, nav.c.stoplength, vaa.terminalflag]).where(
            and_(
                (vaa.fcode != text(":coastal_fcode")),
                (nav.c.terminalflag != 1),
                (vaa.pathlength + vaa.lengthkm >= nav.c.stoplength),
                or_(vaa.hydroseq == nav.c.dnhydroseq, and_(nav.c.dnminorhyd != 0, vaa.hydroseq == nav.c.dnminorhyd)),
            )
        )
    )
    # Create the final query
    query = select([nav_dd.c.comid]).select_from(nav_dd)

    return query.params(distance=distance, comid=comid, coastal_fcode=coastal_fcode)


def navigate_um(
    comid: int,
    distance: float | None,
    coastal_fcode: int,
) -> sqlalchemy.sql.selectable.Select:
    LOGGER.debug(f"Creating navigation query for UM mode: {comid=}, {distance=}, {coastal_fcode=}")
    nav = (
        select(

                FlowlineVAAModel.comid,
                FlowlineVAAModel.levelpathid,
                FlowlineVAAModel.uphydroseq,
                FlowlineVAAModel.fcode,
                (FlowlineVAAModel.pathlength + text(":distance")).label("stoplength"),  # noqa

        )
        .where(FlowlineVAAModel.comid == text(":comid"))
        .cte("nav", recursive=True)
    )

    vaa = aliased(FlowlineVAAModel, name="x")
    nav_um = nav.union(
        select(vaa.comid, vaa.levelpathid, vaa.uphydroseq, vaa.fcode, nav.c.stoplength).where(
            and_(
                (vaa.hydroseq == nav.c.uphydroseq),
                (vaa.levelpathid == nav.c.levelpathid),
                (vaa.fcode != text(":coastal_fcode")),
                (vaa.pathlength <= nav.c.stoplength),
            )
        )
    )

    # Create the final query
    query = select(nav_um.c.comid).select_from(nav_um)

    return query.params(distance=distance, comid=comid, coastal_fcode=coastal_fcode)


def navigate_ut(
    comid: int,
    distance: float | None,
    coastal_fcode: int,
) -> sqlalchemy.sql.selectable.Select:
    LOGGER.debug(f"Creating navigation query for UT mode: {comid=}, {distance=}, {coastal_fcode=}")
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

    vaa = aliased(FlowlineVAAModel, name="x")
    nav_ut = nav.union(
        select([vaa.comid, vaa.hydroseq, vaa.startflag, vaa.fcode, nav.c.stoplength]).where(
            and_(
                (vaa.fcode != text(":coastal_fcode")),
                (nav.c.startflag != 1),
                (vaa.pathlength <= nav.c.stoplength),
                or_(vaa.dnhydroseq == nav.c.hydroseq, and_(vaa.dnminorhyd != 0, vaa.dnminorhyd == nav.c.hydroseq)),
            )
        )
    )
    # Create the final query
    query = select([nav_ut.c.comid]).select_from(nav_ut)

    return query.params(distance=distance, comid=comid, coastal_fcode=coastal_fcode)


def trim_navigation(
    nav_mode: str,
    comid: int,
    trim_tolerance: float,
    measure: float,
) -> sqlalchemy.sql.selectable.Select:
    scaled_measure = 1 - ((measure - FlowlineModel.fmeasure) / (FlowlineModel.tmeasure - FlowlineModel.fmeasure))

    if nav_mode in [NavigationModes.DD, NavigationModes.DM]:
        geojson = func.ST_AsGeoJSON(func.ST_LineSubstring(FlowlineModel.shape, scaled_measure, 1), 9, 0)
    elif nav_mode in [NavigationModes.UT, NavigationModes.UM]:
        geojson = func.ST_AsGeoJSON(func.ST_LineSubstring(FlowlineModel.shape, 0, scaled_measure), 9, 0)

    if 100 - measure >= trim_tolerance:
        LOGGER.debug("Forming trim query")
        nav_trim = case(
            (FlowlineModel.nhdplus_comid == text(":comid"), geojson), else_=func.ST_AsGeoJSON(FlowlineModel.shape, 9, 0)
        )

        query = select([FlowlineModel.nhdplus_comid.label("comid"), nav_trim.label("geojson")])
    else:
        query = select(
            [FlowlineModel.nhdplus_comid.label("comid"), func.ST_AsGeoJSON(FlowlineModel.shape, 9, 0).label("geojson")]
        )

    return query.params(comid=comid)
