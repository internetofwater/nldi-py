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

"""Module containing the models for NLDI Lookup functions"""

import logging
from sqlalchemy import select, text, and_, func

from nldi.schemas.nhdplus import FlowlineModel as Flow
from nldi.schemas.nldi_data import FeatureSourceModel as Feature
from nldi.schemas.nldi_data import CrawlerSourceModel as Crawler

LOGGER = logging.getLogger(__name__)


def estimate_measure(feature_id: str, feature_source: str):
    query = select([
        Flow.fmeasure +
        (1 - func.ST_LineLocatePoint(Flow.shape, Feature.location)) *
        (Flow.tmeasure - Flow.fmeasure).label('measure')
    ]).join(
        Feature,
        and_(
            Feature.comid == Flow.nhdplus_comid,
            Feature.identifier == text(':feature_id'),
        )
    ).join(
        Crawler,
        and_(
            Crawler.source_suffix == text(':feature_source'),
            Feature.crawler_source_id == Crawler.crawler_source_id  # noqa
        )
    )

    return query.params(
        feature_id=feature_id,
        feature_source=feature_source
    )


def get_distance_from_flowline(feature_id: str, feature_source: str):
    x = select([
        Flow.shape,
        Feature.location
    ]).join(
        Feature,
        and_(
            Feature.comid == Flow.nhdplus_comid,
            Feature.identifier == text(':feature_id'),
        )
    ).join(
        Crawler,
        and_(
            Crawler.source_suffix == text(':feature_source'),
            Feature.crawler_source_id == Crawler.crawler_source_id  # noqa
        )
    )

    query = select([
        func.ST_Distance(x.c.location, x.c.shape, False)
    ])

    return query.params(
        feature_id=feature_id,
        feature_source=feature_source
    )


def get_point_on_flowline(feature_id: str, feature_source: str):
    point = func.ST_LineInterpolatePoint(
        Flow.shape,
        (1 - (
            (Feature.measure - Flow.fmeasure) /
            (Flow.tmeasure - Flow.fmeasure))
         )
    )

    query = select([
        func.ST_X(point).label('lon'),
        func.ST_Y(point).label('lat')
    ]).join(
        Feature,
        and_(
            Feature.comid == Flow.nhdplus_comid,
            Feature.identifier == text(':feature_id'),
        )
    ).join(
        Crawler,
        and_(
            Crawler.source_suffix == text(':feature_source'),
            Feature.crawler_source_id == Crawler.crawler_source_id  # noqa
        )
    )

    return query.params(
        feature_id=feature_id,
        feature_source=feature_source
    )


def get_closest_point_on_flowline(feature_id: str, feature_source: str):
    x = select([
        Flow.shape.label('shape'),
        Feature.location.label('location')
    ]).join(
        Feature,
        and_(
            Feature.comid == Flow.nhdplus_comid,
            Feature.identifier == text(':feature_id'),
        )
    ).join(
        Crawler,
        and_(
            Crawler.source_suffix == text(':feature_source'),
            Feature.crawler_source_id == Crawler.crawler_source_id
        )
    ).alias('x')

    point = select([
        func.ST_Closestpoint(x.c.shape, x.c.location).label('point')
    ]).alias('point')

    query = select([
        func.ST_X(point.c.point).label('lon'),
        func.ST_Y(point.c.point).label('lat')
    ]).alias('result')

    return query.params(
        feature_id=feature_id,
        feature_source=feature_source
    )
