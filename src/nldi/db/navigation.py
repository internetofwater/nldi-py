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
