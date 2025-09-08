#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
""" """

from sqlalchemy.orm import Session

from .catchment import CatchmentService
from .feature import FeatureService
from .flowline import FlowlineService
from .pygeoapi import PyGeoAPIService


class BasinService:
    SPLIT_CATCHMENT_THRESHOLD = 200

    def __init__(self, session: Session, pygeoapi_url: str):
        self._service_url = pygeoapi_url
        self._session = session
        self.flowline_svc = FlowlineService(session=self._session)
        self.catchment_svc = CatchmentService(session=self._session)
        self.feature_svc = FeatureService(session=self._session)
        self.pygeoapi_svc = PyGeoAPIService(session=self._session, pygeoapi_url=pygeoapi_url)

    def _get_start_comid(self, identifier: str, source_name: str) -> tuple[int, bool]:
        try:
            if source_name.lower() == "comid":
                _ = self.flowline_svc.get(identifier)  # just making sure it exists. Will raise KeyError if not.
                start_comid = int(identifier)
                is_point = False
                feature = None  # sentinal; indicates not a feature lookup.
            else:
                hit = self.feature_svc.feature_lookup(source_name, identifier)
                feature = hit.as_feature()
                start_comid = int(feature.properties["comid"])
                is_point = feature.geometry["type"] == "Point"
        except (ValueError, TypeError):
            msg = f"Unexpected error getting comid from {identifier} / {source_name}"
            logging.debug(msg)
            raise LookupError(msg)
        except KeyError:
            msg = f"The feature {identifier} does not exist for '{source_name}'."  # noqa
            logging.debug(msg)
            raise LookupError(msg)
        return (start_comid, is_point, feature)

    def get_by_id(
        self,
        identifier: str,
        source_name: str | None = None,
        simplified: bool = False,
        split: bool = False,
    ):
        """
        Calculate basin from a specific feature.

        This method will return a list of features that represent the basin upstream
        from the given feature.  The feature is first identified by its source and
        unique id.  The upstream surface area is calculated, which may require that
        the catchment be split if the feature is a point.

        The return of this method is a list of GeoJSON features, suitable for creating
        a ``FeatureCollection``.  In all cases, the list will contain exactly one
        feature.
        """
        source_name = source_name.lower() if source_name else "comid"
        try:
            (start_comid, is_point, feature) = self._get_start_comid(identifier, source_name)
        except LookupError:
            logging.debug(f"Cannot get starting COMID for {identifier} / {source_name}")
            raise # this is not our problem. Let the caller sort it out.

        if is_point and split:
            # Plan A: the point is on a FlowLine
            point = self.flowline_svc.feat_get_point_along_flowline(identifier, source_name)

            if point is None:
                ## Plan B:
                ## No point on flowline found.... trying to find nearest point
                try:
                    distance = self.flowline_svc.feat_get_distance_from_flowline(identifier, source_name)
                    if distance <= self.SPLIT_CATCHMENT_THRESHOLD:
                        point = self.flowline_svc.feat_get_nearest_point_on_flowline(identifier, source_name)
                except (LookupError, TypeError, ValueError):
                    raise LookupError(f"Unexpected error finding point on flowline: {identifier} / {source_name}")

            if point is None:  # Still
                ## Plan C:
                # assert feature is not None
                try:
                    [lon, lat] = feature["geometry"]["coordinates"]
                    wkt_geom = f"POINT({lon} {lat})"
                    response = self.pygeoapi_svc.hydrolocation_by_coords(wkt_geom)
                    point = response["features"][0]["geometry"]["coordinates"]
                except (LookupError, TypeError, ValueError):
                    raise LookupError(f"Unexpected error decoding hydrolocation for {wkt_geom}")

            if point is None:  ## still no point; not much we can do here.
                raise LookupError("Unable to retrieve point on flowline for catchment splitting.")

            [lon, lat] = point
            wkt_geom = f"POINT({lon} {lat})"
            features = [self.pygeoapi_svc.splitcatchment_at_coords(wkt_geom)]
        else:
            # The feature in question is not a point, and should be associated with a basin by COMID.
            try:
                feature = self.catchment_svc.get_drainage_basin_by_comid(start_comid, simplified)
            except KeyError as e:
                raise LookupError(f"Cannot get drainage basin by comid. {start_comid=}") from e
            features = [feature]
        return features


