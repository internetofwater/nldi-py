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


class CrawlerSourcePlugin(APIPlugin):
    def __init__(self, db_info):
        super().__init__(db_info)
        self.table_model = CrawlerSourceModel

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
            q = self.query(session)
            return [self._to_feature_dict(item) for item in q.all()]

    def _to_feature_dict(self, item) -> Dict[str, Any]:
        # Add properties from item
        item_dict = item.__dict__
        item_dict.pop("_sa_instance_state")  # Internal SQLAlchemy metadata
        return item_dict

    def insert_source(self, source, session=None) -> None:
        """
        Update a source in the database.

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

    # def align_sources(self, sources: List[Dict[str, str]]) -> bool:
    #     """
    #     Align the sources in the database with the provided list of sources.

    #     This will delete all sources in the database and replace them with the sources
    #     in the provided list. The list is assumed to be well-formatted with valid
    #     sources and all keys/columns present.
    #     """
    #     with Session(self._engine) as session:
    #         try:
    #             session.query(CrawlerSourceModel).delete()
    #             session.commit()
    #             [self._align_source(session, source) for source in sources]
    #         except ProgrammingError as err:
    #             LOGGER.warning(err)
    #             raise ProviderQueryError(err)

    #     return True

