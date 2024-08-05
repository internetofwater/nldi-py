#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

from contextlib import contextmanager
from functools import cached_property
from typing import Dict

import sqlalchemy
from sqlalchemy.engine import URL as DB_URL
from sqlalchemy.orm import sessionmaker

from .. import LOGGER


class BaseHandler:
    """
    Handle lookups to a Postgresql database.

    Connection based on psycopg2 using sync approach and server
    side cursor (using support class DatabaseCursor)
    """

    DIALECT = "postgresql+psycopg2" # Default SQL dialect/driver for all handlers

    def __init__(self, db_info: Dict[str, str]):
        LOGGER.debug("%s Constructor", self.__class__.__name__)
        # Read table information from database
        self.geom_field = None
        self.id_field = None
        self.table_model = None
        self.db_search_path = []
        self._store_db_parameters(db_info)

    def get(self, identifier, **kwargs):
        raise NotImplementedError()

    def query(self, **kwargs):
        raise NotImplementedError()

    def insert(self, **kwargs):
        raise NotImplementedError()

    def update(self, **kwargs):
        raise NotImplementedError()

    def lookup_navigation(self, nav: str):
        raise NotImplementedError()

    @contextmanager
    def session(self, raw=False):
        try:
            Session = sessionmaker(bind=self._engine)
            session = Session()
            if raw is True:
                yield session
            elif self.geom_field:
                geom = sqlalchemy.func.ST_AsGeoJSON(self.geom_field).label("geom")
                yield session.query(self.table_model, geom)
            else:
                yield session.query(self.table_model)
        finally:
            session.close()

    def _store_db_parameters(self, parameters:Dict[str, str]) -> None:
        self.db_user = parameters.get("user")
        self.db_host = parameters.get("host")
        self.db_port = parameters.get("port", 5432)
        self.db_name = parameters.get("dbname")
        self._db_password = parameters.get("password")

    @cached_property
    def db_connection_string(self) -> DB_URL:
        return DB_URL.create(
            self.DIALECT,
            username=self.db_user,
            password=self._db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )

    @cached_property
    def _engine(self) -> sqlalchemy.engine :
        engine = sqlalchemy.create_engine(
            self.db_connection_string,
            connect_args={"client_encoding": "utf8", "application_name": "nldi"},
            pool_pre_ping=True,
        )
        return engine

    def __repr__(self) -> str:
        return "<BaseLookup>"

    def _heartbeat(self) -> bool:
        """
        Validate connection to the DB.

        :return: success/failure
        :rtype: bool
        """
        with self._engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
