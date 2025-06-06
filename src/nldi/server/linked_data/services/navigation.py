#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""Navigation business logic service layer"""

from contextlib import contextmanager
from enum import StrEnum
from typing import Any, Generator, Self

import geoalchemy2
import sqlalchemy
from advanced_alchemy.exceptions import NotFoundError
from sqlalchemy import and_, case, func, or_, select, text
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql.expression import Select

from nldi.db.schemas.nhdplus import CatchmentModel, FlowlineModel, FlowlineVAAModel
from nldi.db.schemas.nldi_data import CrawlerSourceModel, FeatureSourceModel

from .... import util
from .crawlersource import CrawlerSourceService
from .feature import FeatureService
from .flowline import FlowlineService

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


class NavigationService:
    def __init__(self, session: Session):
        self._session = session
        self.feature_svc = FeatureService(session=self._session)
        self.source_svc = CrawlerSourceService(session=self._session)
        self.flowline_svc = FlowlineService(session=self._session)

    @classmethod
    @contextmanager
    def new(
        cls,
        session: Session | None = None,
    ) -> Generator[Self, None, None]:
        if not session:
            raise AdvancedAlchemyError(detail="Please supply an optional configuration or session to use.")
        if session:
            yield cls(
                session=session,
            )

    def navigation(
        self,
        nav_mode: NavigationModes,
        comid: int,
        distance: float | None = None,
        coastal_fcode: int = COASTAL_FCODE,
    ) -> sqlalchemy.sql.selectable.Select:
        """
        Create a **query** for navigation.

        This method -- or rather the methods which this method shims -- will produce a sqlalchemy
        ``Select`` appropriate to find the relevant features, given the nav mode, distance, and
        starting point.  The query must still be executed against the database at some point.

        This method's sole purpose is to shim the call to the appropriate navigation function, based
        on the value of the ``nav_mode`` parameter. See the various modal methods below for details
        of each of those queryies.
        """
        _modes = {
            NavigationModes.DM: self.dm,
            NavigationModes.DD: self.dd,
            NavigationModes.UM: self.um,
            NavigationModes.UT: self.ut,
        }
        if nav_mode not in _modes:
            raise ValueError(f"Invalid navigation mode: {nav_mode}.  Mode must be one of {self.modes}.")
        else:
            func = _modes[nav_mode]
        return func(comid, distance, coastal_fcode)

    @property
    def modes(self) -> list[NavigationModes]:
        """List all of the valid navigation modes"""
        return [k for k in NavModesDesc]

    def dm(
        self,
        comid: int,
        distance: float | None,
        coastal_fcode: int = COASTAL_FCODE,
    ) -> sqlalchemy.sql.selectable.Select:
        """Create a navigation query for the DM navigation mode."""
        nav = (
            select(
                FlowlineVAAModel.comid,
                FlowlineVAAModel.terminalpathid,
                FlowlineVAAModel.dnhydroseq,
                FlowlineVAAModel.fcode,
                (FlowlineVAAModel.pathlength + FlowlineVAAModel.lengthkm - text(":distance")).label("stoplength"),  # noqa
            )
            .where(FlowlineVAAModel.comid == text(":comid"))
            .cte("nav", recursive=True)
        )

        vaa = aliased(FlowlineVAAModel, name="vaa")
        nav_dm = nav.union(
            select(vaa.comid, vaa.terminalpathid, vaa.dnhydroseq, vaa.fcode, nav.c.stoplength).where(
                and_(
                    (vaa.hydroseq == nav.c.dnhydroseq),
                    (vaa.terminalpathid == nav.c.terminalpathid),
                    (vaa.fcode != text(":coastal_fcode")),
                    (vaa.pathlength + vaa.lengthkm >= nav.c.stoplength),
                )
            )
        )

        query = select(nav_dm.c.comid).select_from(nav_dm)
        # # should compile to something like:
        # """
        # WITH RECURSIVE nav(comid, terminalpathid, dnhydroseq, fcode, stoplength) AS
        #     (
        #     SELECT nhdplus.plusflowlinevaa_np21.comid AS comid,
        #         nhdplus.plusflowlinevaa_np21.terminalpathid AS terminalpathid,
        #         nhdplus.plusflowlinevaa_np21.dnhydroseq AS dnhydroseq,
        #         nhdplus.plusflowlinevaa_np21.fcode AS fcode,
        #         (nhdplus.plusflowlinevaa_np21.pathlength + nhdplus.plusflowlinevaa_np21.lengthkm) - :distance AS stoplength
        #     FROM nhdplus.plusflowlinevaa_np21
        #         WHERE nhdplus.plusflowlinevaa_np21.comid = :comid
        #     UNION
        #     SELECT vaa.comid AS comid,
        #         vaa.terminalpathid AS terminalpathid,
        #         vaa.dnhydroseq AS dnhydroseq,
        #         vaa.fcode AS fcode,
        #         nav.stoplength AS stoplength
        #     FROM nhdplus.plusflowlinevaa_np21 AS vaa, nav
        #         WHERE vaa.hydroseq = nav.dnhydroseq
        #             AND vaa.terminalpathid = nav.terminalpathid
        #             AND vaa.fcode != :coastal_fcode
        #             AND vaa.pathlength + vaa.lengthkm >= nav.stoplength
        #     )
        #     SELECT nav.comid
        #     FROM nav
        #
        ## which will produce a list of COMID values matching the flowlines which associate with the starting comid and distance
        return query.params(distance=distance, comid=comid, coastal_fcode=coastal_fcode)

    def dd(
        self,
        comid: int,
        distance: float | None,
        coastal_fcode: int = COASTAL_FCODE,
    ) -> sqlalchemy.sql.selectable.Select:
        """Build nav query for DD mode."""
        nav = (
            select(
                FlowlineVAAModel.comid,
                FlowlineVAAModel.dnhydroseq,
                FlowlineVAAModel.dnminorhyd,
                FlowlineVAAModel.fcode,
                (FlowlineVAAModel.pathlength + FlowlineVAAModel.lengthkm - text(":distance")).label("stoplength"),  # noqa
                FlowlineVAAModel.terminalflag,
            )
            .where(FlowlineVAAModel.comid == text(":comid"))
            .cte("nav", recursive=True)
        )
        vaa = aliased(FlowlineVAAModel, name="vaa")
        nav_dd = nav.union(
            select(vaa.comid, vaa.dnhydroseq, vaa.dnminorhyd, vaa.fcode, nav.c.stoplength, vaa.terminalflag).where(
                and_(
                    (vaa.fcode != text(":coastal_fcode")),
                    (nav.c.terminalflag != 1),
                    (vaa.pathlength + vaa.lengthkm >= nav.c.stoplength),
                    or_(
                        vaa.hydroseq == nav.c.dnhydroseq, and_(nav.c.dnminorhyd != 0, vaa.hydroseq == nav.c.dnminorhyd)
                    ),
                )
            )
        )
        query = select(nav_dd.c.comid).select_from(nav_dd)
        return query.params(distance=distance, comid=comid, coastal_fcode=coastal_fcode)

    def um(
        self,
        comid: int,
        distance: float | None,
        coastal_fcode: int = COASTAL_FCODE,
    ) -> sqlalchemy.sql.selectable.Select:
        """Build nav query for UM mode."""
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
        vaa = aliased(FlowlineVAAModel, name="vaa")
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
        query = select(nav_um.c.comid).select_from(nav_um)
        return query.params(distance=distance, comid=comid, coastal_fcode=coastal_fcode)

    def ut(
        self,
        comid: int,
        distance: float | None,
        coastal_fcode: int = COASTAL_FCODE,
    ) -> sqlalchemy.sql.selectable.Select:
        """Build nav query for UT mode."""
        nav = (
            select(
                FlowlineVAAModel.comid,
                FlowlineVAAModel.hydroseq,
                FlowlineVAAModel.startflag,
                FlowlineVAAModel.fcode,
                (FlowlineVAAModel.pathlength + text(":distance")).label("stoplength"),  # noqa
            )
            .where(FlowlineVAAModel.comid == text(":comid"))
            .cte("nav", recursive=True)
        )

        vaa = aliased(FlowlineVAAModel, name="vaa")
        nav_ut = nav.union(
            select(vaa.comid, vaa.hydroseq, vaa.startflag, vaa.fcode, nav.c.stoplength).where(
                and_(
                    (vaa.fcode != text(":coastal_fcode")),
                    (nav.c.startflag != 1),
                    (vaa.pathlength <= nav.c.stoplength),
                    or_(vaa.dnhydroseq == nav.c.hydroseq, and_(vaa.dnminorhyd != 0, vaa.dnminorhyd == nav.c.hydroseq)),
                )
            )
        )
        query = select(nav_ut.c.comid).select_from(nav_ut)
        return query.params(distance=distance, comid=comid, coastal_fcode=coastal_fcode)

    def trim_nav_query(
        self,
        nav_mode: str,
        comid: int,
        trim_tolerance: float,
        measure: float,
    ) -> sqlalchemy.sql.selectable.Select:
        """Build a query for trimming features from a named COMID source."""
        # This is a percentage
        scaled_measure = 1 - ((measure - FlowlineModel.fmeasure) / (FlowlineModel.tmeasure - FlowlineModel.fmeasure))

        if nav_mode in [NavigationModes.DD, NavigationModes.DM]:
            geojson = func.ST_AsGeoJSON(func.ST_LineSubstring(FlowlineModel.shape, scaled_measure, 1), 9, 0)
        elif nav_mode in [NavigationModes.UT, NavigationModes.UM]:
            geojson = func.ST_AsGeoJSON(func.ST_LineSubstring(FlowlineModel.shape, 0, scaled_measure), 9, 0)
        # geojson gets the feature's geometry, trimmed/clipped to either its upstream or downstream portion (depending)
        # on the nav mode.

        if 100 - measure >= trim_tolerance:
            nav_trim = case(
                (FlowlineModel.nhdplus_comid == text(":comid"), geojson),
                else_=func.ST_AsGeoJSON(FlowlineModel.shape, 9, 0),
            )
            query = select(FlowlineModel.nhdplus_comid.label("comid"), nav_trim.label("trimmed_geojson"))
        else:
            query = select(
                FlowlineModel.nhdplus_comid.label("comid"),
                func.ST_AsGeoJSON(FlowlineModel.shape, 9, 0).label("trimmed_geojson"),
            )
        return query.params(comid=comid)

    def estimate_measure(self, feature_id: str, feature_source: str):
        """Build a SQL query for estimating meaure on a feature/source."""
        query = (
            select(
                (
                    FlowlineModel.fmeasure
                    + (1 - func.ST_LineLocatePoint(FlowlineModel.shape, FeatureSourceModel.location))
                    * (FlowlineModel.tmeasure - FlowlineModel.fmeasure)
                ).label("measure")
            )
            .join(
                FeatureSourceModel,
                and_(
                    FeatureSourceModel.comid == FlowlineModel.nhdplus_comid,
                    FeatureSourceModel.identifier == text(":feature_id"),
                ),
            )
            .join(
                CrawlerSourceModel,
                and_(
                    sqlalchemy.func.lower(CrawlerSourceModel.source_suffix) == text(":feature_source"),
                    FeatureSourceModel.crawler_source_id == CrawlerSourceModel.crawler_source_id,  # noqa
                ),
            )
        )
        q = query.params(feature_id=feature_id, feature_source=feature_source.lower())
        hits = self.flowline_svc.repository._execute(q)
        _r = hits.fetchone()[0]
        return _r

    def walk_flowlines(
        self,
        source_name: str,
        identifier: str,
        nav_mode: str,
        distance: float,
        trim_start: bool = False,
        trim_tolerance: float = 0.0,
    ):
        if source_name == "comid":
            if trim_start:
                raise ValueError("Cannot use 'trim_start' with 'comid' source features.")
            starting_flowline = self.flowline_svc.get(identifier)
            if not starting_flowline:
                raise NotFoundError
            start_comid = int(starting_flowline.nhdplus_comid)
        else:
            starting_feature = self.feature_svc.feature_lookup(source_name, identifier)
            if not starting_feature:
                raise NotFoundError
            start_comid = int(starting_feature.comid)

        nav_results_query = self.navigation(nav_mode, start_comid, distance)

        if trim_start is True:
            measure = starting_feature.measure
            if not measure:  # only happens if measure is supplied as zero
                measure = self.estimate_measure(identifier, source_name)
            measure = float(measure)
            trim_nav_q = self.trim_nav_query(nav_mode, start_comid, trim_tolerance, measure)
            features = self.flowline_svc.trimed_features_from_nav_query(nav_results_query, trim_nav_q)
        else:
            features = self.flowline_svc.features_from_nav_query(nav_results_query)

        return features

    def walk_features(
        self,
        source_name: str,
        identifier: str,
        nav_mode: str,
        return_source: str,
        distance: float,
    ):
        if source_name == "comid":
            starting_flowline = self.flowline_svc.get(identifier)
            if not starting_flowline:
                raise NotFoundError
            start_comid = int(starting_flowline.nhdplus_comid)
        else:
            starting_feature = self.feature_svc.feature_lookup(source_name, identifier)
            if not starting_feature:
                raise NotFoundError
            start_comid = int(starting_feature.comid)

        nav_results_query = self.navigation(nav_mode, start_comid, distance)

        features = self.feature_svc.features_from_nav_query(return_source, nav_results_query)
        return features


def navigation_svc(db_session: Session) -> Generator[NavigationService, None, None]:
    """Provider function as part of the dependency-injection mechanism."""
    with NavigationService.new(session=db_session) as service:
        yield service
