#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
#
"""Common lookup queries for the NLDI database"""

from sqlalchemy import and_, func, select, text

from nldi.schemas.nhdplus import FlowlineModel as Flow
from nldi.schemas.nldi_data import CrawlerSourceModel as Crawler
from nldi.schemas.nldi_data import FeatureSourceModel as Feature

from .. import LOGGER


def estimate_measure(feature_id: str, feature_source: str):
    """Build a SQL query for estimating meaure on a feature/source."""
    query = (
        select(
            [
                Flow.fmeasure
                + (1 - func.ST_LineLocatePoint(Flow.shape, Feature.location))
                * (Flow.tmeasure - Flow.fmeasure).label("measure")
            ]
        )
        .join(
            Feature,
            and_(
                Feature.comid == Flow.nhdplus_comid,
                Feature.identifier == text(":feature_id"),
            ),
        )
        .join(
            Crawler,
            and_(
                Crawler.source_suffix == text(":feature_source"),
                Feature.crawler_source_id == Crawler.crawler_source_id,  # noqa
            ),
        )
    )

    return query.params(feature_id=feature_id, feature_source=feature_source)


def distance_from_flowline(feature_id: str, feature_source: str):
    """Build SQL query to find distance from a flowline."""
    x = (
        select([Flow.shape, Feature.location])
        .join(
            Feature,
            and_(
                Feature.comid == Flow.nhdplus_comid,
                Feature.identifier == text(":feature_id"),
            ),
        )
        .join(
            Crawler,
            and_(
                Crawler.source_suffix == text(":feature_source"),
                Feature.crawler_source_id == Crawler.crawler_source_id,  # noqa
            ),
        )
    )

    query = select([func.ST_Distance(x.c.location, x.c.shape, False)])

    return query.params(feature_id=feature_id, feature_source=feature_source)


def point_on_flowline(feature_id: str, feature_source: str):
    """Build a SQL query to find point on flowline."""
    point = func.ST_LineInterpolatePoint(
        Flow.shape, (1 - ((Feature.measure - Flow.fmeasure) / (Flow.tmeasure - Flow.fmeasure)))
    )

    query = (
        select([func.ST_X(point).label("lon"), func.ST_Y(point).label("lat")])
        .join(
            Feature,
            and_(
                Feature.comid == Flow.nhdplus_comid,
                Feature.identifier == text(":feature_id"),
            ),
        )
        .join(
            Crawler,
            and_(
                Crawler.source_suffix == text(":feature_source"),
                Feature.crawler_source_id == Crawler.crawler_source_id,  # noqa
            ),
        )
    )

    return query.params(feature_id=feature_id, feature_source=feature_source)


def closest_point_on_flowline(feature_id: str, feature_source: str):
    """Build a SQL query to find point on a flowline."""
    x = (
        select([Flow.shape.label("shape"), Feature.location.label("location")])
        .join(
            Feature,
            and_(
                Feature.comid == Flow.nhdplus_comid,
                Feature.identifier == text(":feature_id"),
            ),
        )
        .join(
            Crawler,
            and_(
                Crawler.source_suffix == text(":feature_source"), Feature.crawler_source_id == Crawler.crawler_source_id
            ),
        )
        .alias("x")
    )

    point = select([func.ST_Closestpoint(x.c.shape, x.c.location).label("point")]).alias("point")

    query = select([func.ST_X(point.c.point).label("lon"), func.ST_Y(point.c.point).label("lat")]).alias("result")

    return query.params(feature_id=feature_id, feature_source=feature_source)
