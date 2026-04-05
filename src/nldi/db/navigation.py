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

    Should compile to::

        WITH RECURSIVE nav(comid, terminalpathid, dnhydroseq, fcode, stoplength) AS (
            SELECT comid, terminalpathid, dnhydroseq, fcode,
                   pathlength + lengthkm - :distance AS stoplength
            FROM nhdplus.plusflowlinevaa_np21 WHERE comid = :comid
            UNION
            SELECT vaa.comid, vaa.terminalpathid, vaa.dnhydroseq, vaa.fcode, nav.stoplength
            FROM nhdplus.plusflowlinevaa_np21 vaa, nav
            WHERE vaa.hydroseq = nav.dnhydroseq
              AND vaa.terminalpathid = nav.terminalpathid
              AND vaa.fcode != :coastal_fcode
              AND vaa.pathlength + vaa.lengthkm >= nav.stoplength
        )
        SELECT nav.comid FROM nav
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

    Should compile to::

        WITH RECURSIVE nav(comid, dnhydroseq, dnminorhyd, fcode, stoplength, terminalflag) AS (
            SELECT comid, dnhydroseq, dnminorhyd, fcode,
                   pathlength + lengthkm - :distance AS stoplength, terminalflag
            FROM nhdplus.plusflowlinevaa_np21 WHERE comid = :comid
            UNION
            SELECT vaa.comid, vaa.dnhydroseq, vaa.dnminorhyd, vaa.fcode,
                   nav.stoplength, vaa.terminalflag
            FROM nhdplus.plusflowlinevaa_np21 vaa, nav
            WHERE (vaa.hydroseq = nav.dnhydroseq
                   OR (nav.dnminorhyd != 0 AND vaa.hydroseq = nav.dnminorhyd))
              AND vaa.fcode != :coastal_fcode
              AND nav.terminalflag != 1
              AND vaa.pathlength + vaa.lengthkm >= nav.stoplength
        )
        SELECT nav.comid FROM nav
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

    Should compile to::

        WITH RECURSIVE nav(comid, levelpathid, uphydroseq, fcode, stoplength) AS (
            SELECT comid, levelpathid, uphydroseq, fcode,
                   pathlength + :distance AS stoplength
            FROM nhdplus.plusflowlinevaa_np21 WHERE comid = :comid
            UNION ALL
            SELECT vaa.comid, vaa.levelpathid, vaa.uphydroseq, vaa.fcode, nav.stoplength
            FROM nhdplus.plusflowlinevaa_np21 vaa, nav
            WHERE vaa.hydroseq = nav.uphydroseq
              AND vaa.levelpathid = nav.levelpathid
              AND vaa.fcode != :coastal_fcode
              AND vaa.pathlength <= nav.stoplength
        )
        SELECT nav.comid FROM nav
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
    nav_um = nav.union_all(
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

    Should compile to::

        WITH RECURSIVE nav(comid, hydroseq, startflag, fcode, stoplength) AS (
            SELECT comid, hydroseq, startflag, fcode,
                   pathlength + :distance AS stoplength
            FROM nhdplus.plusflowlinevaa_np21 WHERE comid = :comid
            UNION
            SELECT vaa.comid, vaa.hydroseq, vaa.startflag, vaa.fcode, nav.stoplength
            FROM nhdplus.plusflowlinevaa_np21 vaa, nav
            WHERE nav.startflag != 1
              AND (vaa.dnhydroseq = nav.hydroseq
                   OR (vaa.dnminorhyd != 0 AND vaa.dnminorhyd = nav.hydroseq))
              AND vaa.fcode != :coastal_fcode
              AND vaa.pathlength <= nav.stoplength
        )
        SELECT nav.comid FROM nav
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


def trim_nav_query(nav_mode: str, comid: int, trim_tolerance: float, measure: float) -> Select:
    """Build a query that produces trimmed geometry for the starting flowline.

    Uses ST_LineSubstring to clip the starting flowline's geometry based on
    the feature's measure. Only the starting comid gets trimmed; other
    flowlines get their full geometry via ST_AsGeoJSON.

    For downstream modes (DM, DD): clip from measure to end of line.
    For upstream modes (UM, UT): clip from start of line to measure.
    """
    from sqlalchemy import case, func, text

    from .models import FlowlineModel

    # Scale measure to a 0-1 fraction along the line
    scaled_measure = 1 - ((measure - FlowlineModel.fmeasure) / (FlowlineModel.tmeasure - FlowlineModel.fmeasure))

    if nav_mode.upper() in ("DM", "DD"):
        trimmed_geojson = func.ST_AsGeoJSON(func.ST_LineSubstring(FlowlineModel.shape, scaled_measure, 1), 9, 0)
        should_trim = 100 - measure >= trim_tolerance
    else:
        trimmed_geojson = func.ST_AsGeoJSON(func.ST_LineSubstring(FlowlineModel.shape, 0, scaled_measure), 9, 0)
        should_trim = measure >= trim_tolerance

    full_geojson = func.ST_AsGeoJSON(FlowlineModel.shape, 9, 0)

    if should_trim:
        geom_expr = case(
            (FlowlineModel.nhdplus_comid == bindparam("trim_comid"), trimmed_geojson),
            else_=full_geojson,
        )
    else:
        geom_expr = full_geojson

    return select(FlowlineModel.nhdplus_comid.label("comid"), geom_expr.label("trimmed_geojson")).params(
        trim_comid=comid
    )


def basin_query(comid: int) -> Select:
    """Upstream basin CTE — walks all tributaries with no distance limit.

    Returns comids of all upstream flowlines. Join to catchmentsp and
    ST_Union the geometries to get the drainage basin polygon.

    Matches Java mybatis stream.xml basin query. Should compile to::

        WITH RECURSIVE nav(comid, hydroseq, startflag) AS (
            SELECT comid, hydroseq, startflag
            FROM nhdplus.plusflowlinevaa_np21
            WHERE comid = :comid
            UNION
            SELECT vaa.comid, vaa.hydroseq, vaa.startflag
            FROM nhdplus.plusflowlinevaa_np21 vaa, nav
            WHERE nav.startflag != 1
              AND (vaa.dnhydroseq = nav.hydroseq
                   OR (vaa.dnminorhyd != 0 AND vaa.dnminorhyd = nav.hydroseq))
        )
        SELECT nav.comid FROM nav
    """
    from sqlalchemy import or_

    nav = (
        select(
            FlowlineVAAModel.comid,
            FlowlineVAAModel.hydroseq,
            FlowlineVAAModel.startflag,
        )
        .where(FlowlineVAAModel.comid == bindparam("comid"))
        .cte("nav", recursive=True)
    )

    vaa = aliased(FlowlineVAAModel, name="vaa")
    nav_basin = nav.union(
        select(vaa.comid, vaa.hydroseq, vaa.startflag).where(
            and_(
                nav.c.startflag != 1,
                or_(
                    vaa.dnhydroseq == nav.c.hydroseq,
                    and_(vaa.dnminorhyd != 0, vaa.dnminorhyd == nav.c.hydroseq),
                ),
            )
        )
    )

    return select(nav_basin.c.comid).select_from(nav_basin).params(comid=comid)
