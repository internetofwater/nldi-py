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

import logging
from contextlib import contextmanager
from typing import Iterable

from sqlalchemy import create_engine, func
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

from nldi.lookup import _ENGINE_STORE

from .. import LOGGER


class BaseLookup:
    """Postgresql database based on psycopg2 using sync approach and server
    side cursor (using support class DatabaseCursor)
    """

    def __init__(self, provider_def):
        """
        BaseLookup Class constructor

        :param provider_def: provider definitions from yml nldi-config.
                             data, id_field, name set in parent class
                             data contains the connection information
                             for class DatabaseCursor

        :returns: nldi.lookup.base.BaseLookup
        """
        LOGGER.debug("Initialising BaseLookup")

        # Read table information from database
        self.geom_field = None
        self.id_field = None
        self.table_model = None
        self.db_search_path = []
        self._store_db_parameters(provider_def["database"])
        self._engine = self._get_engine()

    def get(self, identifier, **kwargs):
        """
        query by id

        :param identifier: feature id

        :returns: dict of single GeoJSON feature
        """
        raise NotImplementedError()

    def query(self, **kwargs):
        """
        query

        :returns: dict of 0..n GeoJSON features or coverage data
        """
        raise NotImplementedError()

    def lookup_navigation(self, nav: str):
        """
        Lookup navigation result from set of comids

        :returns: dict of 0..n GeoJSON features or coverage data
        """
        raise NotImplementedError()

    @contextmanager
    def session(self, raw=False):
        try:
            Session = sessionmaker(bind=self._engine)
            session = Session()
            if raw is True:
                yield session
            elif self.geom_field:
                geom = func.ST_AsGeoJSON(self.geom_field).label("geom")
                yield session.query(self.table_model, geom)
            else:
                yield session.query(self.table_model)
        finally:
            session.close()

    def _store_db_parameters(self, parameters):
        self.db_user = parameters.get("user")
        self.db_host = parameters.get("host")
        self.db_port = parameters.get("port", 5432)
        self.db_name = parameters.get("dbname")
        self._db_password = parameters.get("password")

    def _get_engine(self):
        """
        Create a SQL Alchemy engine for the database and reflect the table
        model.  Use existing versions from stores if available to allow reuse
        of Engine connection pool and save expensive table reflection.
        """
        # One long-lived engine is used per database URL:
        # https://docs.sqlalchemy.org/en/14/core/connections.html#basic-usage
        engine_store_key = (self.db_user, self.db_host, self.db_port, self.db_name)
        try:
            engine = _ENGINE_STORE[engine_store_key]
        except KeyError:
            LOGGER.debug("Storing engine connection")
            conn_str = URL.create(
                "postgresql+psycopg2",
                username=self.db_user,
                password=self._db_password,
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
            )
            engine = create_engine(
                conn_str, connect_args={"client_encoding": "utf8", "application_name": "nldi"}, pool_pre_ping=True
            )
            _ENGINE_STORE[engine_store_key] = engine

        return engine

    def __repr__(self):
        return "<BaseLookup>"


class ProviderGenericError(Exception):
    """provider generic error"""

    pass


class ProviderConnectionError(ProviderGenericError):
    """provider connection error"""

    pass


class ProviderTypeError(ProviderGenericError):
    """provider type error"""

    pass


class ProviderInvalidQueryError(ProviderGenericError):
    """provider invalid query error"""

    pass


class ProviderQueryError(ProviderGenericError):
    """provider query error"""

    pass


class ProviderItemNotFoundError(ProviderGenericError):
    """provider item not found query error"""

    pass
