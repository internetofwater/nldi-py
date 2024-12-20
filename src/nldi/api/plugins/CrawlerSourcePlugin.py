#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#
# See the full copyright notice in LICENSE.md

"""Plugin to search and manipulate crawler sources."""

from typing import Any, Dict, List

import sqlalchemy
from sqlalchemy.dialects.postgresql import insert as pginsert

from ... import LOGGER
from ...schemas.nldi_data import CrawlerSourceModel
from .APIPlugin import APIPlugin


class CrawlerSourcePlugin(APIPlugin):
    """
    API Plugin for managing the Crawler Source table.

    This plugin is required for much of the NLDI functionality, since it provides the
    information about the sources of the data that NLDI uses. It is not registered as
    a plugin in the API (although it could be), but is instead used directly by the API
    as its ``.sources`` attribute.  See the API class for more information.

    Crawler sources do not have a spatial component, so this plugin does not have the
    ``get_by_coords()`` method that is present in the other plugins.  It does have the
    ``get_by_id()`` method, which is used to retrieve a source by its ``source_suffix``.
    It also includes a method to retrieve all sources in the table.

    Unlike other plugins, this plugin has a method to insert a source into the database (all
    other plugins are read-only). These update/write methods are not plumbed to endpoints
    in the API, so they are not exposed to the outside world.  They are used internally to
    manage the sources table.
    """

    def __init__(self, name: str | None = None, **kwargs: Dict[str, Any]):
        super().__init__(name, **kwargs)
        self.table_model = CrawlerSourceModel

    def get_by_id(self, identifier: str) -> Dict[str, Any]:
        """
        Retrieve a source from the database.

        **IMPORTANT!!!**  Note that the identifier supplied as an argument to this method is
        the source's ``source_suffix``.  This is treated as a unique identifier by the
        business logic of the NLDI API, but there is actually **NO** unique constraint
        on this column in the database.  This column is NOT the primary key for the crawler
        source table.  The primary key is the ``crawler_source_id`` column, which is an
        integer value.
        """
        ## TODO: single-dispatch method to handle different types of identifiers.
        #    * for strings, do as we do now.
        #    * for ints, do the query against the primary key.
        source_name = identifier.lower()
        LOGGER.debug(f"GET information for source with suffix: {source_name}")

        with self.session() as session:
            # Retrieve data from database as feature
            q = self.query(session)
            source_suffix = sqlalchemy.func.lower(CrawlerSourceModel.source_suffix)
            item = q.filter(source_suffix == source_name).first()
            if item is None:
                raise KeyError(f"No such source: {source_name=}.")
                # NOTE: I switched from the custom "notfound" exception to the more standard KeyError, as this is how
                # most python code is written (i.e. a KeyError is raised when a key is not found in a dictionary).
        return self._to_feature_dict(item)

    def get_all(self) -> List[Dict[str, str]]:
        """
        List all items in the CrawlerSource table.

        Produces a list of dictionaries, each dictionary representing a row in the table.
        Note that we are choosing to return the data as a list of dictionaries, rather than
        as a generator.  The sources table is small, and this approach simplifies the code
        use a fair bit.

        :return: A list of dictionaries, each representing a row in the CrawlerSource table.
        :rtype: List[Dict[str, str]]
        """
        LOGGER.debug(f"GET all sources from {self.table_model.__tablename__}")
        with self.session() as session:
            q = self.query(session).order_by(CrawlerSourceModel.crawler_source_id)
            return [self._to_feature_dict(item) for item in q.all()]

    def _to_feature_dict(self, item) -> Dict[str, Any]:
        """Convert a SQLAlchemy model object to a dictionary."""
        item_dict = item.__dict__
        item_dict.pop("_sa_instance_state")  # Internal SQLAlchemy metadata
        return item_dict

    def insert_source(self, source: Dict[str, str]) -> bool:
        """
        Insert a source in the CrawlerSource table.

        This method will insert a new source into the database, or update an existing source
        if it happens to have the same ``crawler_source_id`` as an existing source.  This
        "upsert" using "ON CONFLICT" clause is specific to the postgres dialect of SQL.

        **NOTE:** that this is a (hopefully) non-breaking change in behavior.  Previous factors of this
        function presumed that the to-be-inserted source did not already exist, and simply
        inserted a new row. In practice, this method is called by the ``align_sources()`` method,
        below, which deletes all sources before inserting new ones.

        :param source: A dictionary representing the source to insert.
        :type source: Dict[str, str]
        :return: True if the source was inserted, False otherwise.
        :rtype: bool
        """
        source_suffix = source["source_suffix"].lower()
        source["source_suffix"] = source_suffix

        try:
            with self.session() as session:
                # helpful resource: https://www.slingacademy.com/article/sqlalchemy-upsert-update-if-exists-insert-if-not/
                insert_stmt = pginsert(CrawlerSourceModel).values(**source)
                upsert_stmt = insert_stmt.on_conflict_do_update(
                    index_elements=["crawler_source_id"],
                    ##              ^^^^^^^^^^^^^^^^^^^ This is the only column with an index or unique constraint.
                    set_={
                        "source_suffix": source["source_suffix"],
                        "source_name": source["source_name"],
                        "source_uri": source["source_uri"],
                        "feature_id": source["feature_id"],
                        "feature_name": source["feature_name"],
                        "feature_uri": source["feature_uri"],
                        "feature_reach": source["feature_reach"],
                        "feature_measure": source["feature_measure"],
                        "ingest_type": source["ingest_type"],
                    },
                )
                session.execute(upsert_stmt)
                session.commit()
        except sqlalchemy.exc.SQLAlchemyError as err:
            LOGGER.error(err)
            return False
        return True

    def delete_source(self, source_id: int) -> bool:
        """
        Delete a named source from the database.

        Note that the source_id is the primary key for the table, so this is the value
        to supply for deletions.  This is not the same as the ``source_suffix``, which is
        in-practice unique, but this is not guaranteed.  The crawler source table has
        no constraints on any columns other than the primary key.

        We see this as a feature in the case of deletions -- you have to get the integer
        ``crawler_source_id`` in order to delete a source; it can't be done with any other
        property/column of the table.

        :param source_id: the ``crawler_source_id`` of the source to delete.
        :type source_id: int
        :return: True if the source was deleted, False otherwise.
        :rtype: bool
        """
        try:
            with self.session() as session:
                source = self.query(session).get(source_id)
                if source is None:
                    LOGGER.warning(f"Source with ID {source_id} not found.")
                    return False
                session.delete(source)
                session.commit()
        except sqlalchemy.exc.SQLAlchemyError as err:
            LOGGER.error(err)
            return False
        return True

    def align_sources(self, sources: List[Dict[str, str]], force: bool = True) -> bool:
        """
        Align the sources in the database with the provided list of sources.

        This uses an "upsert" (using the ``insert_source()`` method) to add sources
        to the database, one at a time. The list is assumed to be well-formatted with
        valid sources and all columns present.

        If the ``force`` parameter is True, all sources in the database will be deleted
        before inserting the new ones. This is the default, as this preserves backward
        compatibility. If False, the new sources will be inserted/updated in the source
        table without purging the existing configuration.

        :param sources: A list of sources to insert into the database.
        :type sources: Dict[str, str]
        :param force: If True, delete all sources in the database before inserting the new ones.
        :type force: bool
        :return: True if the sources were inserted, False otherwise.
        :rtype: bool
        """
        if force:
            # Delete all sources in the crawler source table and replace them with the provided list.
            with self.session() as session:
                session.query(CrawlerSourceModel).delete()
                session.commit()
        for s in sources:
            # I agree.... a single session for all of these would be better than letting insert_source
            # create a new session for each insert.... but we're only talking about inserting a dozen
            # rows at most.
            self.insert_source(s)  ##TODO: optimize this to allow session re-use.
        return True
