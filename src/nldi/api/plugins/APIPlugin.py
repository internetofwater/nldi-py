from contextlib import contextmanager
from typing import Any, Dict, List

import sqlalchemy
from sqlalchemy.engine import URL as DB_URL
from sqlalchemy.orm import Session

from ... import LOGGER


class APIPlugin:
    def __init__(self, name: str | None = None, **kwargs: Dict[str, Any]):
        LOGGER.debug(f"{self.__class__.__name__} Constructor")
        self.name = name if name else self.__class__.__name__
        self.parent = None

        self._db_connect_url = kwargs.get("db_connect_url")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    def get_by_id(self, id: str) -> Any:
        raise NotImplementedError

    def get_by_coords(self, coords: str) -> Any:
        raise NotImplementedError

    @property
    def is_registered(self) -> bool:
        return self.parent is not None

    @property
    def base_url(self) -> str:
        if self.is_registered:
            return self.parent.config["base_url"]
        else:
            LOGGER.warning("Attempt to get base_url from an unregistered plugin.")
            return "/"

    @property
    def _db_engine(self) -> sqlalchemy.engine:
        """
        Get the database engine for the plugin.

        If the plugin is registered, we get the database engine from the parent.  This is the intended
        normal mode of operation. If the plugin is not registered, we create a new database engine
        using the connection URL provided in the constructor.  Assuming that one was provided.  This
        pattern of creating a new engine is intended for use in testing and development only.  Plugins
        are meant to be used as a component of the API and should not be creating their own database
        engines except in bizzare circumstances.

        Note that this method is named with a leading underscore to indicate that it is intended for
        internal use only.  It is not part of the public API of the plugin, precisely because it is
        only ever used by the plugin itself.

        :raises RuntimeError: If no database connection URL is provided and none can be found from the parent.
        :return: engine
        :rtype: sqlalchemy.engine
        """
        if self.is_registered:
            return self.parent.db_engine
        else:
            LOGGER.warning("Attempt to get db_engine from an unregistered plugin.")
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
        Make a session for the plugin's database engine.

        This is a convenience method to create a session object for the plugin's
        database engine.  I've moved away from ``sessionmaker`` because it is
        more flexible to create the session object directly. And a sqlalchemy
        ``Session`` is already a context manager (so we don't have to worry about
        closing it, so log as it is used correctly.)

        :raises RuntimeError: _description_
        :return: _description_
        :rtype: _type_
        """
        return sqlalchemy.orm.Session(self._db_engine)

    def query(self, session) -> sqlalchemy.orm.query.Query:
        ## TODO:  I am reconsidering the need for this method.
        """
        Make a ``sqlalchemy`` query object for the plugin's table model.

        We are asking for the session to be passed in rather than relying on
        self.session() to create it. This is to allow for the possibility of
        using the same session for multiple queries or for non-query operations
        like add, update, delete.

        This query object is the foundation for higher level methods such
        as ``get``.

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
            return nrows >= 1
        else:
            ## if no table defined, we just run a dummy query to see if the connection is working.
            try:
                with self._db_engine.connect() as c:
                    c.execute("SELECT 1")
            except sqlalchemy.exc.OperationalError as e:
                LOGGER.error(f"Database connection error: {e}")
                return False
            return True
