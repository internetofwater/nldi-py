# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Navigation query builders — recursive CTEs for network traversal.

Each function returns a SQLAlchemy Select that produces a list of COMIDs
along the navigation path. The query must be executed against the database
and joined to FlowlineModel or FeatureSourceModel to produce results.

See docs/implementation-notes.md for readability notes.
"""

from enum import StrEnum

from sqlalchemy import Select, and_, bindparam, select
from sqlalchemy.orm import aliased

from .models import FlowlineVAAModel

COASTAL_FCODE = 56600


class NavigationModes(StrEnum):
    """Valid navigation modes."""

    DM = "DM"
    DD = "DD"
    UM = "UM"
    UT = "UT"


NAV_DIST_DEFAULTS = {
    NavigationModes.DM: 100_000,
    NavigationModes.UM: 100_000,
    NavigationModes.UT: 100,
    NavigationModes.DD: 100,
}


def dm(comid: int, distance: float, coastal_fcode: int = COASTAL_FCODE) -> Select:
    """Downstream Main navigation CTE.

    Walks downstream following the main channel (dnhydroseq) on the same
    terminal path. Stops when distance is exceeded or coastal fcode is reached.
    """
    nav = (
        select(
            FlowlineVAAModel.comid,
            FlowlineVAAModel.terminalpathid,
            FlowlineVAAModel.dnhydroseq,
            FlowlineVAAModel.fcode,
            (FlowlineVAAModel.pathlength + FlowlineVAAModel.lengthkm - bindparam("distance")).label("stoplength"),
        )
        .where(FlowlineVAAModel.comid == bindparam("comid"))
        .cte("nav", recursive=True)
    )

    vaa = aliased(FlowlineVAAModel, name="vaa")
    nav_dm = nav.union(
        select(
            vaa.comid,
            vaa.terminalpathid,
            vaa.dnhydroseq,
            vaa.fcode,
            nav.c.stoplength,
        ).where(
            and_(
                vaa.hydroseq == nav.c.dnhydroseq,
                vaa.terminalpathid == nav.c.terminalpathid,
                vaa.fcode != bindparam("coastal_fcode"),
                vaa.pathlength + vaa.lengthkm >= nav.c.stoplength,
            )
        )
    )

    return (
        select(nav_dm.c.comid).select_from(nav_dm).params(comid=comid, distance=distance, coastal_fcode=coastal_fcode)
    )


def dd(comid: int, distance: float, coastal_fcode: int = COASTAL_FCODE) -> Select:
    """Downstream with Diversions navigation CTE.

    Walks downstream following both main channel (dnhydroseq) and diversions
    (dnminorhyd). Stops at distance, coastal fcode, or terminal flag.
    """
    nav = (
        select(
            FlowlineVAAModel.comid,
            FlowlineVAAModel.dnhydroseq,
            FlowlineVAAModel.dnminorhyd,
            FlowlineVAAModel.fcode,
            (FlowlineVAAModel.pathlength + FlowlineVAAModel.lengthkm - bindparam("distance")).label("stoplength"),
            FlowlineVAAModel.terminalflag,
        )
        .where(FlowlineVAAModel.comid == bindparam("comid"))
        .cte("nav", recursive=True)
    )

    vaa = aliased(FlowlineVAAModel, name="vaa")
    from sqlalchemy import or_

    nav_dd = nav.union(
        select(vaa.comid, vaa.dnhydroseq, vaa.dnminorhyd, vaa.fcode, nav.c.stoplength, vaa.terminalflag).where(
            and_(
                vaa.fcode != bindparam("coastal_fcode"),
                nav.c.terminalflag != 1,
                vaa.pathlength + vaa.lengthkm >= nav.c.stoplength,
                or_(
                    vaa.hydroseq == nav.c.dnhydroseq,
                    and_(nav.c.dnminorhyd != 0, vaa.hydroseq == nav.c.dnminorhyd),
                ),
            )
        )
    )

    return (
        select(nav_dd.c.comid).select_from(nav_dd).params(comid=comid, distance=distance, coastal_fcode=coastal_fcode)
    )


def um(comid: int, distance: float, coastal_fcode: int = COASTAL_FCODE) -> Select:
    """Upstream Main navigation CTE.

    Walks upstream following the main channel (uphydroseq) on the same
    level path. Stops when distance is exceeded or coastal fcode is reached.
    """
    nav = (
        select(
            FlowlineVAAModel.comid,
            FlowlineVAAModel.levelpathid,
            FlowlineVAAModel.uphydroseq,
            FlowlineVAAModel.fcode,
            (FlowlineVAAModel.pathlength + bindparam("distance")).label("stoplength"),
        )
        .where(FlowlineVAAModel.comid == bindparam("comid"))
        .cte("nav", recursive=True)
    )

    vaa = aliased(FlowlineVAAModel, name="vaa")
    nav_um = nav.union(
        select(vaa.comid, vaa.levelpathid, vaa.uphydroseq, vaa.fcode, nav.c.stoplength).where(
            and_(
                vaa.hydroseq == nav.c.uphydroseq,
                vaa.levelpathid == nav.c.levelpathid,
                vaa.fcode != bindparam("coastal_fcode"),
                vaa.pathlength <= nav.c.stoplength,
            )
        )
    )

    return (
        select(nav_um.c.comid).select_from(nav_um).params(comid=comid, distance=distance, coastal_fcode=coastal_fcode)
    )


def ut(comid: int, distance: float, coastal_fcode: int = COASTAL_FCODE) -> Select:
    """Upstream with Tributaries navigation CTE.

    Walks upstream following all tributaries (any segment whose dnhydroseq
    matches the current hydroseq). Stops at distance, coastal fcode, or startflag.
    """
    from sqlalchemy import or_

    nav = (
        select(
            FlowlineVAAModel.comid,
            FlowlineVAAModel.hydroseq,
            FlowlineVAAModel.startflag,
            FlowlineVAAModel.fcode,
            (FlowlineVAAModel.pathlength + bindparam("distance")).label("stoplength"),
        )
        .where(FlowlineVAAModel.comid == bindparam("comid"))
        .cte("nav", recursive=True)
    )

    vaa = aliased(FlowlineVAAModel, name="vaa")
    nav_ut = nav.union(
        select(vaa.comid, vaa.hydroseq, vaa.startflag, vaa.fcode, nav.c.stoplength).where(
            and_(
                vaa.fcode != bindparam("coastal_fcode"),
                nav.c.startflag != 1,
                vaa.pathlength <= nav.c.stoplength,
                or_(
                    vaa.dnhydroseq == nav.c.hydroseq,
                    and_(vaa.dnminorhyd != 0, vaa.dnminorhyd == nav.c.hydroseq),
                ),
            )
        )
    )

    return (
        select(nav_ut.c.comid).select_from(nav_ut).params(comid=comid, distance=distance, coastal_fcode=coastal_fcode)
    )


def navigation_query(mode: str, comid: int, distance: float) -> Select:
    """Dispatch to the appropriate navigation CTE by mode."""
    builders = {"DM": dm, "DD": dd, "UM": um, "UT": ut}
    builder = builders.get(mode.upper())
    if not builder:
        msg = f"Invalid navigation mode: {mode}. Must be one of {', '.join(builders)}"
        raise ValueError(msg)
    return builder(comid, distance)
