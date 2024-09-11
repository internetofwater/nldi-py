from contextlib import contextmanager
from typing import Any, Dict, List

import sqlalchemy
from sqlalchemy.engine import URL as DB_URL

from .. import LOGGER
from ..schemas.nldi_data import CrawlerSourceModel
from .BasePlugin import APIPlugin


class CrawlerSourcePlugin(APIPlugin):
    def __init__(self, name):
        super().__init__(name)
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

