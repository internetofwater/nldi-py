#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""API Plugin Base Class"""

from contextlib import contextmanager
from typing import Any, Dict, List

import sqlalchemy
from sqlalchemy.engine import URL as DB_URL
from sqlalchemy.orm import Session

from ... import LOGGER


class APIPlugin:
    """
    Base class for all API plugins.

    The various plugins that make up the NLDI API are all subclasses of this class.  It
    provides a common interface for all plugins, including methods for getting data from the
    database, and for checking the status of the database connection.  Any lookup or query
    operation that is common to all plugins should be implemented here.

    The APIPlugin class is intentionally **NOT** an abstract base class.  It is possible
    to create an instance of this class, but this would have no purpose for real-world use.
    This class can be instantiated for testing and development purposes, but in normal
    operation, it is intended to be subclassed.

    The initializer for this class takes a single optional argument, ``name``, which
    is a string that is used to identify the plugin in the ``API`` plugin registry. If
    no name is provided, the name is taken to be the name of the class itself.

    Optionally, the initializer can take a keyword argument, ``db_connect_url``, which is a
    connection URL for the database it should use to perform its queries.  This parameter
    is typicall not used, as the plugin design calls for it to use the parent's (i.e. the
    ``API`` database connection).  Specifying a ``db_connect_url`` in the intializer is
    useful during testing and development, when the plugin may not be registered with
    the API.
    """

    def __init__(self, name: str | None = None, **kwargs: Dict[str, Any]):
        LOGGER.debug(f"{self.__class__.__name__} Constructor")
        self.name = name if name else self.__class__.__name__
        self.parent = None

        self._db_connect_url = kwargs.get("db_connect_url")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    @property
    def is_registered(self) -> bool:
        """
        Test to see if the plugin is registered with an API.

        :return: True if the plugin is registered, False otherwise.
        :rtype: bool
        """
        return self.parent is not None

    def get_by_id(self, id: str) -> Any:
        """
        Get a record from the database by its ID.

        This is a generic method for getting a record from the database by its ID.  In
        this base class, it is not implemented, but it is intended to be implemented in
        subclasses. Exactly what an "ID" is will depend on the plugin, as will the
        return type (Geojson, ORM object, etc.)

        :param id: A plugin-specific identifier for the record to find.
        :type id: str
        :raises NotImplementedError: This method is not implemented in the base class.
        :return: The record that matches the ID.
        :rtype: Any
        """
        raise NotImplementedError

    def get_by_coords(self, coords: str) -> Any:
        """
        Get a record from the database by its coordinates.

        This is a generic method for getting a record from the database by its spatial
        location.  The coordinates are passed as a string in the form of a WKT point (e.g.
        ``POINT(123.0 45.0)``.

        For some plugins, the coordinates may be used to query a database table for a
        record that contains the point.  For other plugins, the idea of a spatial search
        may not make sense, and this method may not be implemented.

        :param coords: A point to use for the search, in WKT format.
        :type coords: str
        :raises NotImplementedError: This method is not implemented in the base class.
        :return: The record that intersect the point spatially.
        :rtype: Any
        """
        raise NotImplementedError

    @property
    def base_url(self) -> str:
        """
        Get the base URL for the plugin.

        The ``base_url`` is used to construct other URLs returned as properties of various
        plugins. The base URL is typically the root URL of the API, but it can be overridden
        by the plugin.  If the plugin is registered with the API, the base URL is taken from
        the API itself -- that information is defined in the global config in the API
        constructor.

        If the plugin is not registered, the base URL is assumed to be
        "/".  This is a fallback for testing and development purposes.

        :return: The base URL for the plugin.
        :rtype: str
        """
        if self.is_registered:
            return self.parent.config["base_url"]
        else:
            LOGGER.info("Attempt to get base_url from an unregistered plugin.")
            return "/"

    @property
    def _db_engine(self) -> sqlalchemy.engine:
        """
        Get the database engine for the plugin.

        If the plugin is registered, we get the database engine from the parent (the API object).
        This is the intended normal mode of operation. If the plugin is not registered, we
        create a new database engine using the connection URL provided in the constructor, assuming
        that one was provided.

        This pattern of creating a new engine is intended for use in testing and development
        only.  Plugins are meant to be used as a component of the API and should not be creating
        their own database engines except in bizzare circumstances.

        :raises RuntimeError: If no database connection URL is provided and none can be found from the parent.
        :return: engine
        :rtype: sqlalchemy.engine
        """
        if self.is_registered:
            return self.parent.db_engine
        else:
            LOGGER.info("Attempt to get db_engine from an unregistered plugin.")
            ## We are an orphaned pluggin, so we need to create our own engine if we can.
            LOGGER.debug(f"{self.__class__.__name__} creating database engine...")
            if not self._db_connect_url:
                raise RuntimeError("No database connection URL provided.")
            engine = sqlalchemy.create_engine(
                self._db_connect_url,
                connect_args={"client_encoding": "utf8", "application_name": "nldi"},
                pool_pre_ping=True,
            )
        return engine

    def session(self) -> Session:
        """
        Make a sqlalchemy session for the plugin's database engine.

        This is a convenience method to create a session object for the plugin's
        database engine.  I've moved away from ``sessionmaker`` because I find it
        more flexible to create the session object directly. And a SQLalchemy
        ``Session`` is already a context manager, so we don't have to worry about
        closing it -- so long as it is used correctly by the caller.

        :return: A session object
        :rtype: sqlalchemy.orm.session.Session
        """
        return sqlalchemy.orm.Session(self._db_engine)

    def query(self, session) -> sqlalchemy.orm.query.Query:
        ## TODO:  I am reconsidering the need for this method.
        """
        Make a ``sqlalchemy`` query object for the plugin's table model.

        This method is deprecated.

        This method is retained for backward compatibility.  It is a convenience method
        which creates a SQLAlchemy ``Query`` object with the table and geometry-as-geojson
        information pre-specified.

        We are moving away from this construct, insisting that the caller explicitly
        define what they want queries to return.

        :param session: An open session object
        :type session: sqlalchemy.orm.session.Session
        :return: A query object
        :rtype: sqlalchemy.orm.query.Query
        """
        if hasattr(self, "geom_field") and self.geom_field:
            geojson = sqlalchemy.func.ST_AsGeoJSON(self.geom_field).label("geojson")
            return session.query(self.table_model, geojson)
        else:
            return session.query(self.table_model)

    def db_is_alive(self) -> bool:
        """
        Validate connection to the DB.

        This method is used to check the status of the database connection.  It is intended as
        a simple health check to see if the plugin will work. It is not a comprehensive test
        of database functionality, but it is a good first step to see if the plugin failed
        to initialize properly.

        :return: success/failure
        :rtype: bool
        """
        if hasattr(self, "table_model"):
            ## If a table is defined, we try to count the rows in the table to see if the connection is working.
            try:
                with self.session() as session:
                    nrows = session.query(self.table_model).count()
                    ## Counting the rows in the table is a simple way to check if the connection is working and the table maps via the ORM.
            except sqlalchemy.exc.OperationalError as e:
                LOGGER.error(f"Database connection error: {e}")
                return False
            success = nrows >= 1
            if success:
                LOGGER.debug(f"Database connection is working: {nrows} rows found.")
            else:
                LOGGER.error(f"Database connection is not working: {nrows} rows found.")
            return success
        else:
            ## if no table defined, we just run a dummy query to see if the connection is working.
            try:
                with self._db_engine.connect() as c:
                    c.execute(sqlalchemy.text("SELECT 1"))
            except sqlalchemy.exc.OperationalError as e:
                LOGGER.error(f"Database connection error: {e}")
                return False
            return True
