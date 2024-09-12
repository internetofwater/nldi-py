#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

"""
PyGeoAPI Plugin


This plugin provides a mechanism for proxying requests to a PyGeoAPI
instance running elsewhere. It is used to provide that pygeoapi functionality
via the NLDI API, without forcing the client to make a separate request to the

"""


from contextlib import contextmanager
from typing import Any, Dict, List

import httpx
import sqlalchemy
from sqlalchemy.engine import URL as DB_URL

from .. import LOGGER
from ..schemas.nldi_data import CrawlerSourceModel
from .BasePlugin import APIPlugin

## TODO: Need to complete catchment lookup before this will work



DEFAULT_PROPS = {
    "identifier": "",
    "navigation": "",
    "measure": "",
    "reachcode": "",
    "name": "",
    "source": "provided",
    "sourceName": "Provided via API call",
    "comid": "",
    "type": "point",
    "uri": "",
}


class PyGeoPlugin(APIPlugin):
    def __init__(self, name):
        super().__init__(name)
        # self.catchment_lookup = provider_def["catchment_lookup"]

    @property
    def pygeoapi_url(self) -> str:
        if self.is_registered:
            return self.parent.config.get('pygeoapi_url', "")
        else:
            LOGGER.error("Attempt to get pygeoapi_url from an unregistered plugin.")
            raise KeyError


    def get_hydrolocation(self, coords: str) -> dict:
        LOGGER.debug(f"Extracting geom from WKT: {coords}")
        point = wkt.loads(coords)
        request_payload = {
            "inputs": [
                {"id": "lon", "type": "text/plain", "value": point.x},
                {"id": "lat", "type": "text/plain", "value": point.y},
                {"id": "direction", "type": "text/plain", "value": "none"},
            ]
        }
        LOGGER.debug("Making OGC API - Processes request")
        url = util.url_join(self.pygeoapi_url, "processes/nldi-flowtrace/execution")
        response = self._post_external_service(url, data=request_payload)

        LOGGER.debug("Getting feature intersection")
        [lon, lat] = response["features"][0]["properties"]["intersection_point"]  # noqa
        wkt_geom = f"POINT({lon} {lat})"
        nhdplus_comid = self.catchment_lookup.query(wkt_geom)
        nav_url = url_join(self.base_url, "linked-data/comid", nhdplus_comid, "navigation")

        LOGGER.debug(f"Getting measure for {nhdplus_comid}")
        measure = (
            FlowlineModel.fmeasure
            + (
                1 - func.ST_LineLocatePoint(FlowlineModel.shape, func.ST_GeomFromText(wkt_geom, 4269))  # noqa
            )
            * (FlowlineModel.tmeasure - FlowlineModel.fmeasure)
        ).label("measure")
        with Session(self._engine) as session:
            result = (
                session.query(measure, FlowlineModel.reachcode)
                .filter(FlowlineModel.nhdplus_comid == nhdplus_comid)
                .first()
            )

            if result is None:
                msg = f"No measure found for: {coords}."
                raise ProviderItemNotFoundError(msg)

            computed_measure = result.measure
            computed_reach = result.reachcode

        fc = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "properties": {
                        "identifier": "",
                        "navigation": nav_url,
                        "measure": computed_measure,
                        "reachcode": computed_reach,
                        "name": "",
                        "source": "indexed",
                        "sourceName": "Automatically indexed by the NLDI",
                        "comid": nhdplus_comid,
                        "type": "hydrolocation",
                        "uri": "",
                    },
                },
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [point.x, point.y]},
                    "properties": DEFAULT_PROPS,
                },
            ],
        }
        return fc

    def get_split_catchment(self, coords: str) -> dict:
        """
        query split catchment

        :param coords: WKT of point element

        :returns: GeoJSON features
        """
        LOGGER.debug(f"Extracting geom from WKT: {coords}")
        point = wkt.loads(coords)
        data = {
            "inputs": [
                {"id": "lon", "type": "text/plain", "value": f"{point.x}"},
                {"id": "lat", "type": "text/plain", "value": f"{point.y}"},
                {"id": "upstream", "type": "text/plain", "value": "true"},
            ]
        }

        LOGGER.debug("Making OGC API - Processes request")
        url = url_join(self.pygeoapi_url, "processes/nldi-splitcatchment/execution")  # noqa
        response = self._get_response(url, data=data)

        for feature in response["features"]:
            if feature["id"] == "mergedCatchment":
                feature.pop("id")
                yield feature

    @staticmethod
    def _post_external_service(url: str, data: dict = {}) -> dict:
        LOGGER.debug(f"Making POST request to: {url}")
        try:
            with httpx.Client() as client:
                r = client.post(url, data=data).raise_for_status()
                response = r.json()
        except httpx.HTTPStatusError as err:
            LOGGER.error(f"HTTP error: {err}")
            raise ProviderQueryError from err
        except json.JSONDecodeError as err:
            LOGGER.error(f"JSON decode error: {err}")
            raise ProviderQueryError from err

        return response

















    def get(self, identifier: str):
        """Retrieve a source from the database."""
        source_name = identifier.lower()
        LOGGER.debug(f"GET information for: {source_name}")

        with self.session() as session:
            # Retrieve data from database as feature
            q = self.query(session)
            source_suffix = sqlalchemy.func.lower(CrawlerSourceModel.source_suffix)
            item = q.filter(source_suffix == source_name).first()
            if item is None:
                raise KeyError(f"No such source: source_suffix={source_name}.")
                # NOTE: I switched from the custom "notfound" exception to the more standard KeyError, as this is how
                # most python code is written (i.e. a KeyError is raised when a key is not found in a dictionary).
        return self._to_feature_dict(item)

    def get_all(self) -> List[Dict]:
        """List all items in the self.table_model table."""
        LOGGER.debug(f"GET all sources from {self.table_model.__tablename__}")
        with self.session() as session:
            q = self.query(session).order_by(CrawlerSourceModel.crawler_source_id)
            return [self._to_feature_dict(item) for item in q.all()]

    def _to_feature_dict(self, item) -> Dict[str, Any]:
        # Add properties from item
        item_dict = item.__dict__
        item_dict.pop("_sa_instance_state")  # Internal SQLAlchemy metadata
        return item_dict

    def insert_source(self, source, session=None) -> None:
        """
        Insert a source in the database.

        :param source: _description_
        :type source: _type_
        """
        if session:
            s = session
        else:
            s = self.session()

        source_suffix = source["source_suffix"].lower()
        source["source_suffix"] = source_suffix
        LOGGER.debug(f"Creating source {source_suffix}")  # noqa
        session.add(CrawlerSourceModel(**source))

        session.commit()
        if not session:
            s.close()
