#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

import pathlib
from copy import deepcopy
from functools import cached_property
from typing import Any, Dict, Tuple

import sqlalchemy
from sqlalchemy.engine import URL as DB_URL

from .. import LOGGER, __version__
from ..util import load_yaml
from .BasePlugin import APIPlugin
from .CrawlerSourcePlugin import CrawlerSourcePlugin


class API:
    """
    The main API class for the NLDI API.

    This class is the main entry point for the NLDI API.  It is responsible for managing the plugins
    that provide the API's functionality.  It also manages the database connection information.
    """

    def __init__(self, globalconfig: dict):
        self.plugins: dict = {}
        self.config = deepcopy(globalconfig)
        # self.db_info = globalconfig["server"]["data"]
        # NOTE:  ^^^^^^^^^^^^^^ We are tracking db connection information at the API level.
        # All plugins will use this connection information, as well as any cached ENGINEs
        self.base_url = globalconfig["base_url"]

        self.sources = CrawlerSourcePlugin("Sources")
        self.sources.parent = self
        # NOTE: the sources table is a plugin, same as the other content plugins, but it is a special
        # case. Without the sources table, there's really not much else to do. So, we will handle it
        # here as a must-have special case in the initializer.
        LOGGER.debug(f"New API instance with db_info: {self.db_connection_string!r}")

    @cached_property
    def db_info(self) -> Dict[str, Any]:
        return self.config["server"]["data"]

    @property
    def db_connection_string(self) -> DB_URL:
        return DB_URL.create(
            "postgresql+psycopg2",  # Default SQL dialect/driver
            username=self.db_info.get("user", "nldi"),
            password=self.db_info.get("password", "changeMe"),
            host=self.db_info.get("host", "localhost"),
            port=self.db_info.get("port", 5432),
            database=self.db_info.get("dbname", "nldi"),
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
        self.plugins[plugin.name] = plugin
        plugin.parent = self
        ## On the "fail-fast" principle, we will check if the plugin can connect to the database before moving on.
        if plugin.db_is_alive():
            LOGGER.info(f"Plugin {plugin.name} registered successfully.")
            return True
        else:
            LOGGER.error(f"Plugin {plugin.name} failed to register.")
            del self.plugins[plugin.name]
            # raise RuntimeError("Plugin {plugin.name} failed to register.")
            ## TODO:  Decide if we want to raise an exception here or just deregister the plugin and return False.
            return False

    # def get_plugins(self) -> Dict[str, APIPlugin]:
    #     return self._plugin_registry

    @property
    def openapi_json(self) -> Dict[str, Any]:
        """
        Generate an OpenAPI document for the API.

        This method will generate an OpenAPI document based on the plugins that have been registered with
        the API.  The document will include all of the paths and tags defined by the plugins.

        :return: OpenAPI document
        :rtype: dict
        """
        OAS_SCHEMAS = load_yaml(pathlib.Path(__file__).parent / "schemas.yaml")
        OAS_PARAMETERS = load_yaml(pathlib.Path(__file__).parent / "parameters.yaml")
        OAS_RESPONSES = load_yaml(pathlib.Path(__file__).parent / "responses.yaml")

        RESPONSES = {  # noqa: N806
            "400": {"$ref": "#/components/responses/400"},
            "404": {"$ref": "#/components/responses/404"},
            "406": {"$ref": "#/components/responses/406"},
            "500": {"$ref": "#/components/responses/500"},
        }
        LOGGER.debug("Generating OpenAPI JSON Specification")

        oas = {
            "openapi": "3.0.1",
            "info": {
                "title": self.config["metadata"]["identification"]["title"],
                "description": self.config["metadata"]["identification"]["description"],
                "x-keywords": ["linked data", "hydrology", "geospatial"],
                "termsOfService": self.config["metadata"]["identification"]["terms_of_service"],
                "contact": {
                    "name": self.config["metadata"]["provider"]["name"],
                    "url": self.config["metadata"]["provider"]["url"],
                },
                "license": self.config["metadata"]["license"]["name"],
                "version": __version__,
            },
            "servers": [
                {"url": self.config["base_url"], "description": self.config["metadata"]["identification"]["title"]},
                {"url": "https://labs.waterdata.usgs.gov/api/nldi", "description": "Network Linked Data Index API"},
                {
                    "url": "https://labs-beta.waterdata.usgs.gov/api/nldi/",
                    "description": "Network Linked Data Index API - Beta",
                },
            ],
            "components": {
                "schemas": OAS_SCHEMAS,
                "responses": OAS_RESPONSES,
                "parameters": OAS_PARAMETERS,
            },
            "tags": [
                {
                    "description": "NLDI home",
                    "externalDocs": {
                        "description": "information",
                        "url": "https://github.com/internetofwater/nldi-services",
                    },
                    "name": "nldi",
                },
                {
                    "description": "NHDPlus Version 2 COMID",
                    "externalDocs": {
                        "description": "information",
                        "url": "https://www.usgs.gov/national-hydrography/national-hydrography-dataset",  # noqa
                    },
                    "name": "comid",
                },
            ],
        }
        paths = dict()
        paths["/"] = {
            "get": {
                "summary": "getLandingPage",
                "description": "Landing page",
                "tags": ["nldi"],
                "operationId": "getLandingPage",
                "responses": {
                    "200": {"description": "OK"},
                    "400": {"$ref": "#/components/responses/400"},
                    "500": {"$ref": "#/components/responses/500"},
                },
            }
        }

        paths["/openapi"] = {
            "get": {
                "summary": "getOpenAPI",
                "description": "This document",
                "tags": ["nldi"],
                "operationId": "getOpenAPI",
                "responses": {
                    "200": {"description": "OK"},
                    "400": {"$ref": "#/components/responses/400"},
                    "500": {"$ref": "#/components/responses/500"},
                },
            }
        }

        paths["/linked-data"] = {
            "get": {
                "summary": "getDataSources",
                "description": "Returns a list of data sources",
                "tags": ["nldi"],
                "operationId": "getDataSources",
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/DataSourceList"}}},
                    },
                    **RESPONSES,
                },
            }
        }
        paths["/linked-data/comid"] = {
            "get": {
                "summary": "ComID_ByCoordinates",
                "description": ("returns the feature closest to a " "provided set of coordinates"),
                "tags": ["comid"],
                "operationId": "ComID_ByCoordinates",
                "parameters": [{"$ref": "#/components/parameters/coords"}],
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Feature"}}},
                    },
                    **RESPONSES,
                },
            }
        }

        paths["/linked-data/comid/{comid}"] = {
            "get": {
                "summary": "ComID_ById",
                "description": ("returns registered feature as WGS84 lat/lon " "GeoJSON if it exists"),
                "tags": ["comid"],
                "operationId": "ComID_ById",
                "parameters": [
                    {
                        "name": "comid",
                        "in": "path",
                        "description": "NHDPlus common identifier",
                        "required": True,
                        "schema": {"type": "integer", "example": 13294314},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/FeatureCollection"  # noqa
                                }
                            },
                            "application/ld+json": {
                                "schema": {
                                    "$ref": "#/components/schemas/FeatureCollection"  # noqa
                                }
                            },
                            "application/vnd.geo+json": {
                                "schema": {
                                    "$ref": "#/components/schemas/FeatureCollection"  # noqa
                                }
                            },
                        },
                    },
                    **RESPONSES,
                },
            }
        }

        oas["paths"] = paths

        return oas

    def __repr__(self):
        return "API(plugins=[{}])".format(", ".join(self.plugins.keys()))

    def __str__(self):
        return "API"
