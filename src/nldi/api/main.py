#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

from functools import cached_property
from typing import Dict

import sqlalchemy
from sqlalchemy.engine import URL as DB_URL

from .. import LOGGER
from .plugin import APIPlugin, CrawlerSourcePlugin

class API:
    """
    The main API class for the NLDI API.

    This class is the main entry point for the NLDI API.  It is responsible for managing the plugins
    that provide the API's functionality.  It also manages the database connection information.
    """

    def __init__(self, db_info:dict):
        self._plugin_registry: dict = {}
        self.db_info = db_info
        # NOTE:  ^^^^^^^^^^^^^^ We are tracking db connection information at the API level.
        # All plugins will use this connection information, as well as any cached ENGINEs

        self.sources =  CrawlerSourcePlugin("Sources")
        self.sources.parent = self
        # NOTE: the sources table is a plugin, same as the other content plugins, but it is a special
        # case. Without the sources table, there's really not much else to do. So, we will handle it
        # here as a must-have special case in the initializer.

    @property
    def db_connection_string(self) -> DB_URL:
        return DB_URL.create(
            "postgresql+psycopg2",  # Default SQL dialect/driver
            username=self.db_info.get("user", "nldi"),
            password=self.db_info.get("password", "changeMe"),
            host=self.db_info.get("host", "localhost"),
            port=self.db_info.get("port", 5432),
            database=self.db_info.get("dbname", "nldi")
        )

    @cached_property
    def db_engine(self) -> sqlalchemy.engine:
        """
        Create a database engine for the API.

        This engine is cached for the life of the API object.  All plugins will use this engine rather
        than creating their own.  Each plugin will have its own session, however.

        :return: Database engine, suitable for use with ``sessionmaker``
        :rtype: sqlalchemy.engine
        """
        LOGGER.debug(f"{self.__class__.__name__} creating database engine...")
        engine = sqlalchemy.create_engine(
            self.db_connection_string,
            connect_args={"client_encoding": "utf8", "application_name": "nldi"},
            pool_pre_ping=True,
        )
        return engine

    def register_plugin(self, plugin: APIPlugin) -> bool:
        self._plugin_registry[plugin.name] = plugin
        plugin.parent = self
        ## On the "fail-fast" principle, we will check if the plugin can connect to the database before moving on.
        if plugin.db_is_alive():
            LOGGER.info(f"Plugin {plugin.name} registered successfully.")
            return True
        else:
            LOGGER.error(f"Plugin {plugin.name} failed to register.")
            del self._plugin_registry[plugin.name]
            # raise RuntimeError("Plugin {plugin.name} failed to register.")
            ## TODO:  Decide if we want to raise an exception here or just deregister the plugin and return False.
            return False

    def get_plugins(self) -> Dict[str, APIPlugin]:
        return self._plugin_registry

    def __repr__(self):
        return "API(plugins=[{}])".format(", ".join(self._plugin_registry.keys()))

    def __str__(self):
        return "API"
