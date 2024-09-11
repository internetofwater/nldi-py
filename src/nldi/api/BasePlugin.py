from contextlib import contextmanager
from typing import Any, Dict, List

import sqlalchemy
from sqlalchemy.engine import URL as DB_URL

from .. import LOGGER
from ..schemas.nldi_data import CrawlerSourceModel


class APIPlugin:
    def __init__(self, name: str):
        LOGGER.debug(f"{self.__class__.__name__} Constructor")
        self.name = name
        self.parent = None

    def __repr__(self):
        return f"APIPlugin({self.name})"

    def __str__(self):
        return f"APIPlugin({self.name})"

    @property
    def is_registered(self):
        if self.parent:
            return True
        return False

    @property
    def base_url(self) -> str:
        if self.is_registered:
            return self.parent.config['base_url']
        else:
            LOGGER.error("Attempt to get base_url from an unregistered plugin.")
            raise KeyError

    def session(self):
        """
        Make a session for the plugin's database engine.

        This is a convenience method to create a session object for the plugin's
        database engine.  I've moved away from ``sessionmaker`` because it is
        more flexible to create the session object directly. And a sqlalchemy
        ``Session`` is already a context manager (so we don't have to worry about
        closing it if it is used correctly.)

        :raises RuntimeError: _description_
        :return: _description_
        :rtype: _type_
        """
        if not self.parent:
            raise RuntimeError("Plugin not registered with API")
        return sqlalchemy.orm.Session(self.parent.db_engine)

    def query(self, session):
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
            geom = sqlalchemy.func.ST_AsGeoJSON(self.geom_field).label("geom")
            return session.query(self.table_model, geom)
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
            return nrows >=1
        else:
            ## if no table defined, we just run a dummy query to see if the connection is working.
            try:
                with self.parent.db_engine.connect() as c:
                    c.execute("SELECT 1")
            except sqlalchemy.exc.OperationalError as e:
                LOGGER.error(f"Database connection error: {e}")
                return False
            return True

