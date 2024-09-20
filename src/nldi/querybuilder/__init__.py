#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
#
"""Query Lookups for NLDI"""

from .. import LOGGER
from .basin_query import basin_from_comid


# from nldi.functions.lookup import (
#     estimate_measure,
#     get_closest_point_on_flowline,
#     get_distance_from_flowline,
#     get_point_on_flowline,
# )
# from nldi.functions.navigate import get_navigation, trim_navigation
# from nldi.lookup import _ENGINE_STORE

# class Functions:
#     """Postgresql database functons for the Hydro Network Linked-Data Index"""

#     def __init__(self, provider_def):
#         """
#         Function Class constructor

#         :param provider_def: provider definitions from yml nldi-config.

#         :returns: nldi.functions.Functions
#         """
#         LOGGER.debug("Initialising Functions")

#         # Read table information from database
#         self._store_db_parameters(provider_def)
#         self._engine = self._get_engine()

#     def get_basin(self, comid: int, simplified: bool):
#         """
#         Perform basin navigation

#         :param comid: start comid
#         :param simplified: bool to simplify geometry

#         :returns: iterator of navigated basin
#         """
#         basin = get_basin(comid, simplified)
#         LOGGER.debug(basin.compile(self._engine))

#         with Session(self._engine) as session:
#             # Retrieve data from database as feature
#             result = session.execute(basin).fetchone()

#             if result is None:
#                 msg = f"No such item: {self.id_field}={comid}"
#                 raise FunctionItemNotFoundError(msg)

#             yield {"type": "Feature", "geometry": json.loads(result.the_geom), "properties": {}}

#     def trim_navigation(self, nav_mode: str, comid: int, trim_tolerance: float, measure: float):
#         """
#         Trim navigation

#         :param nav: navigation query
#         :param nav_mode: navigation mode
#         :param comid: start comid
#         :param trim_tolerance: trim tolerance
#         :param measure: calculated measure

#         :returns: string of trimmed navigation query
#         """
#         trim = trim_navigation(nav_mode, comid, trim_tolerance, measure)
#         LOGGER.debug(trim.compile(self._engine))
#         return trim

#     def get_navigation(self, nav_mode: str, comid: int, distance: float):
#         """
#         Perform navigation

#         :param nav_mode: navigation mode
#         :param comid: start comid
#         :param distance: distance to navigate

#         :returns: string of navigation query
#         """
#         try:
#             distance = float(distance)
#         except ValueError:
#             msg = f"Invalid distance: {distance}"
#             LOGGER.error(msg)
#             raise FunctionInvalidQueryError(msg)

#         nav = get_navigation(nav_mode, comid, distance)
#         LOGGER.debug(nav.compile(self._engine))
#         return nav

#     def get_point(self, feature_id: str, feature_source: str):
#         """
#         Perform flowline lookup

#         :param feature_id: Feature indentifier
#         :param feature_source: Feature source

#         :returns: Point on flowline
#         """
#         point = get_point_on_flowline(feature_id, feature_source)
#         LOGGER.debug(point.compile(self._engine))

#         with Session(self._engine) as session:
#             # Retrieve data from database as feature
#             result = session.execute(point).fetchone()

#             if result is None or None in result:
#                 LOGGER.warning("Not on flowline")
#             else:
#                 return result

#     def estimate_measure(self, feature_id: str, feature_source: str):
#         """
#         Perform flowline approximation

#         :param feature_id: Feature indentifier
#         :param feature_source: Feature source

#         :returns: Point on flowline
#         """
#         measure = estimate_measure(feature_id, feature_source)
#         LOGGER.debug(measure.compile(self._engine))

#         with Session(self._engine) as session:
#             # Retrieve data from database as feature
#             result = session.execute(measure).scalar()

#             if result is None:
#                 LOGGER.warning("Not on flowline")
#             else:
#                 return result

#     def get_closest(self, feature_id: str, feature_source: str):
#         """
#         Perform flowline approximation

#         :param feature_id: Feature indentifier
#         :param feature_source: Feature source

#         :returns: Point on flowline
#         """
#         point = get_closest_point_on_flowline(feature_id, feature_source)
#         LOGGER.debug(point.compile(self._engine))

#         with Session(self._engine) as session:
#             # Retrieve data from database as feature
#             result = session.execute(point).fetchone()

#             if None in result:
#                 LOGGER.warning("Not on flowline")
#             else:
#                 return result

#     def get_distance(self, feature_id: str, feature_source: str):
#         """
#         Perform flowline distance

#         :param feature_id: Feature indentifier
#         :param feature_source: Feature source

#         :returns: Distance from nearest flowline
#         """
#         point = get_distance_from_flowline(feature_id, feature_source)
#         LOGGER.debug(point.compile(self._engine))

#         with Session(self._engine) as session:
#             # Retrieve data from database as feature
#             result = session.execute(point).scalar()

#             if result is None:
#                 LOGGER.warning("Not on flowline")
#             else:
#                 return result

#     def _store_db_parameters(self, parameters):
#         self.db_user = parameters.get("user")
#         self.db_host = parameters.get("host")
#         self.db_port = parameters.get("port", 5432)
#         self.db_name = parameters.get("dbname")
#         self._db_password = parameters.get("password")

#     def _get_engine(self):
#         """
#         Create a SQL Alchemy engine for the database and reflect the table
#         model.  Use existing versions from stores if available to allow reuse
#         of Engine connection pool and save expensive table reflection.
#         """
#         # One long-lived engine is used per database URL:
#         # https://docs.sqlalchemy.org/en/14/core/connections.html#basic-usage
#         engine_store_key = (self.db_user, self.db_host, self.db_port, self.db_name)
#         try:
#             engine = _ENGINE_STORE[engine_store_key]
#         except KeyError:
#             LOGGER.debug("Storing engine connection")
#             conn_str = URL.create(
#                 "postgresql+psycopg2",
#                 username=self.db_user,
#                 password=self._db_password,
#                 host=self.db_host,
#                 port=self.db_port,
#                 database=self.db_name,
#             )
#             engine = create_engine(
#                 conn_str, connect_args={"client_encoding": "utf8", "application_name": "nldi"}, pool_pre_ping=True
#             )
#             _ENGINE_STORE[engine_store_key] = engine

#         return engine

#     def __repr__(self):
#         return "<Function>"

