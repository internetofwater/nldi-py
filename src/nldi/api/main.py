#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""API Main Object"""

import importlib
import pathlib
from copy import deepcopy
from functools import cached_property
from typing import Any, Dict, Tuple

import sqlalchemy
from sqlalchemy.engine import URL as DB_URL

from .. import LOGGER, __version__, util
from . import plugins


class API:
    """
    The main API class for NLDI services.

    This class is the main entry point for the NLDI API. It is responsible for
    managing the various plugins which provide the API's functionality.  It also
    shared resources used by those plugins, most notably the database connection.

    An API object is created with a configuration dictionary. This dictionary
    is loaded from a YAML file at runtime, and is structured/modeled on the config
    dictionary used in ``pygeoapi`` applications.  Important keys and sub-keys in
    the config dictionary are:

    * server

      * data

        * dbname
        * host
        * password
        * port
        * user

    * metadata

      * identification

        * title
        * description
        * terms_of_service

    The ``server.data`` dictionary contains the connection information for the
    API's database.

    The ``metadta.identification`` dictionary contains information used to construct
    the OpenAPI document for the API.

    """

    def __init__(self, globalconfig: dict):
        self.plugins: dict = {}
        self.config = deepcopy(globalconfig)

        self.base_url = globalconfig["base_url"]

        self.sources = plugins.CrawlerSourcePlugin("PrivateSources")
        self.sources.parent = self
        # NOTE: the sources table is a plugin, same as the other content plugins, but it is a special
        # case. Without the sources table, there's really not much else to do. So, we will handle it
        # here as a must-have special case in the initializer.

        LOGGER.info(f"New API instance with db_info: {self.db_connection_string!r}")

    @cached_property
    def db_info(self) -> Dict[str, Any]:
        """
        Get database connection information from the global configuration.

        The returned dictionary is a copy of the dict found in ``server.data`` of
        the global configuration.  That is, it contains keys for ``dbname``,
        ``host``, ``password``, ``port``, and ``user``.

        This property is maintined mostly for backward compatibility -- some utility functions
        want the database information in this form. The preferred way to access the database
        connection information is via the ``db_connection_string`` property.

        :return: Database connection information
        :rtype: dict
        """
        return self.config["server"]["data"]

    @property
    def db_connection_string(self) -> DB_URL:
        """
        Compose a database connection string from the configuration info dictionary.

        This property is a pre-formatted and validated connection string for the API's database,
        as may be used to create a database engine in SQLAlchemy.  This implies that the
        API object may connect to exactly one database for the life of the object.

        :return: Database connection string
        :rtype: sqlalchemy.engine.URL
        """
        return DB_URL.create(
            "postgresql+psycopg2",  # Default SQL dialect/driver
            username=self.db_info.get("user", "nldi"),
            password=self.db_info.get("password", "changeMe"),
            host=self.db_info.get("host", "localhost"),
            port=self.db_info.get("port", 5432),
            database=self.db_info.get("dbname", "nldi"),
        )

    @cached_property
    def db_engine(self) -> sqlalchemy.engine.Engine:
        """
        Create a database engine for the API.

        The database engine is a SQLAlchemy data structure used to track details of the
        database connection. It is used later when it comes time to form individual
        sessions in which queries are executed. The ``db_engine`` is re-used by all
        registered plugins as a way of economizing on this datastructure (only one
        engine is needed, as everything connects to the same db server).

        **IMPORTANT** this property is *cached*, so that new engines are not created
        whenever this property is referenced. Repeated access to this property of the
        ``API`` will return the same engine each time rather than creating a new engine.

        :return: Database engine, suitable for use with a session maker.
        :rtype: sqlalchemy.engine.Engine
        """
        LOGGER.debug(f"{self.__class__.__name__} creating database engine...")
        engine = sqlalchemy.create_engine(
            self.db_connection_string,
            connect_args={
                "client_encoding": "utf8",
                "application_name": "nldi",
                "connect_timeout": 20,  ## seconds to wait for a connection
                # TODO: is 20 seconds enough time?
            },
            pool_pre_ping=True,
        )
        return engine

    def register_plugin(self, plugin: plugins.APIPlugin) -> bool:
        """
        Register a plugin with the API.

        The plugins are how individual services are "attached" to this ``API``. Registering a
        plugin enrolls it in an internal data structure. The registry of plugins is nothing
        more than a python dictionary. The key is the plugin's class name (which can be over-ridden
        at the plugin level) and the value is the plugin object itself. Registration
        gives the plugins access to the API's database connection information, its config
        information, etc.

        For this system to work, each registered plugin must have a ``parent`` attribute,
        which will point back to this API object, and it must implement the ``db_is_alive``
        method.  See more information in the ``APIPlugin`` class description.

        :param plugin: The plugin to register
        :type plugin: plugins.APIPlugin
        :return: Success or Failure of registration
        :rtype: bool
        """
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

    def require_plugin(self, plugin_name: str) -> bool:
        """
        Direct the API to load a plugin.

        This method is used to load a plugin that has not yet been registered with the API.  The
        plugin is loaded by name, and then registered with the API.  If the plugin is already
        registered, this method does nothing.

        :param plugin_name: The name of the plugin to load
        :type plugin_name: str
        :raises ImportError: If unable to load the required module
        :raises RuntimeError: If unable to register the plugin
        :return: indication of success
        :rtype: bool
        """
        LOGGER.debug(f"Required plugin: {plugin_name}")
        if plugin_name not in self.plugins:
            LOGGER.info(f"Required plugin {plugin_name} not found in registry.  Attempting to load...")
        else:
            return True  # << already registered; we're done here.

        try:
            pkgname = ".plugins"
            classname = plugin_name
            module = importlib.import_module(pkgname, package="nldi.api")
            class_ = getattr(module, classname)
            plugin = class_()
        except ImportError as e:
            LOGGER.error(f"Failed to load plugin {plugin_name}", exc_info=True)
            raise ImportError(f"Failed to load plugin {plugin_name}") from e

        if self.register_plugin(plugin):
            pass
        else:
            LOGGER.error(f"Failed to register pluging {plugin_name}", exc_info=True)
            raise RuntimeError(f"Failed to register {plugin_name}")
        return True

    @property
    def openapi_json(self) -> Dict[str, Any]:
        """
        Generate an OpenAPI document for the API.

        This method will generate an OpenAPI JSON document based on the information
        found in the global configuration supplied in the constructor. The structure
        of the OAS document and the included endpoints match the current NLDI spec.
        Those paths are largely hard-coded in this method rather than being dynamically
        generated by the currently-loaded plugins. This is because plugins only load
        when they are needed, yet we still need to generate the OpenAPI document for
        services that are not yet loaded.

        Note that the OpenAPI document is generated as a dictionary, not as a JSON string
        (despite the name of the method suggesting json output). The dictionary must be
        serialized to JSON as a part of the Flask framework (using ``jsonify`` or similar).

        :return: OpenAPI document
        :rtype: Dict[str, Any]
        """
        # TODO: load the endpoint descriptions from docstrings -- perhaps one function in the API per endpoint?
        # This would require that we add methods here for each endpoint, which might be a good idea for other
        # reasons as well.  It would also give us consistent docstring format for the plugins.

        OAS_SCHEMAS = util.load_yaml(pathlib.Path(__file__).parent / "schemas.yaml")  # noqa: N806
        OAS_PARAMETERS = util.load_yaml(pathlib.Path(__file__).parent / "parameters.yaml")  # noqa: N806
        OAS_RESPONSES = util.load_yaml(pathlib.Path(__file__).parent / "responses.yaml")  # noqa: N806

        RESPONSES = {  # noqa: N806
            "400": {"$ref": "#/components/responses/400"},
            "404": {"$ref": "#/components/responses/404"},
            "406": {"$ref": "#/components/responses/406"},
            "500": {"$ref": "#/components/responses/500"},
        }
        LOGGER.info("Generating OpenAPI JSON Specification")

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

        tags = [
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
                "name": "by_comid",
            },
            {
                "description": "Lookups by source ID",
                "name": "by_sourceid",
            },
        ]

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
        paths["/linked-data/hydrolocation"] = {
            "get": {
                "summary": "getHydrologicLocation",
                "description": ("Returns the hydrologic location closest to " "a provided set of coordinates."),
                "tags": ["nldi"],
                "operationId": "getHydrologicLocation",
                "parameters": [{"$ref": "#/components/parameters/coords"}],
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/FeatureCollection"  # noqa
                                }
                            }
                        },
                    },
                    **RESPONSES,
                },
            }
        }

        ## A set of paths per source --
        # comid_source = {"source_suffix": "comid", "source_name": "NHDPlus COMID"}
        # all_sources = [comid_source, *self.config["sources"]]
        source_names_enumerated = {source["source_suffix"]: source for source in self.config["sources"]}
        # LOGGER.info(f"Generating paths for {len(all_sources)} sources: {[k['source_suffix'] for k in all_sources]}")

        paths["/linked-data/comid/position"] = {
            "get": {
                "summary": "ComidByCoordinates",
                "description": ("returns the feature closest to a provided set of coordinates"),
                "tags": ["by_comid"],
                "operationId": "ComidByCoordinates",
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
                "summary": f"ComidById",
                "description": ("returns registered feature as WGS84 lat/lon GeoJSON if it exists"),
                "tags": ["by_comid"],
                "operationId": f"ComidById",
                "parameters": [
                    {"$ref": "#/components/parameters/comid"},
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

        paths["/linked-data/{sourceid}/{identifier}"] = {
            "get": {
                "summary": "SourceFeatureById",
                "description": ("returns registered feature as WGS84 lat/lon " "GeoJSON if it exists"),
                "tags": ["by_sourceid"],
                "operationId": f"SourceFeatureById",
                "parameters": [
                    {"$ref": "#/components/parameters/identifier"},
                    {"$ref": "#/components/parameters/sourceid"},
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

        for src in ["comid", "{sourceid}"]:
            base_path = f"/linked-data/{src}"
            src_name = "Source" if src == "{sourceid}" else "comid"
            id_field = "{comid}" if src == "comid" else "{identifier}"
            params = [
                {"$ref": "#/components/parameters/simplified"},
                {"$ref": "#/components/parameters/splitCatchment"},
                {"$ref": "#/components/parameters/identifier"}
                if src == "{sourceid}"
                else {"$ref": "#/components/parameters/comid"},
            ]
            if src == "{sourceid}":
                params.append({"$ref": "#/components/parameters/sourceid"})

            paths[f"{base_path}/{id_field}/basin"] = {
                "get": {
                    "summary": f"{src_name}Basin",
                    "description": ("returns the aggregated basin for the specified feature in WGS84 lat/lon GeoJSON"),
                    "tags": ["by_comid" if src == "comid" else "by_sourceid"],
                    "operationId": f"{src_name}Basin",
                    "parameters": params,
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
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

            paths[f"{base_path}/{id_field}/navigation"] = {
                "get": {
                    "summary": f"{src_name}NavigationOptions",
                    "description": "returns valid navigation end points",
                    "tags": ["by_comid" if src == "comid" else "by_sourceid"],
                    "operationId": f"{src_name}NavigationOptions",
                    "parameters": [
                        {"$ref": "#/components/parameters/identifier"}
                        if src == "{sourceid}"
                        else {"$ref": "#/components/parameters/comid"},
                    ],
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object", "additionalProperties": {"type": "object"}}
                                }
                            },
                        },
                        **RESPONSES,
                    },
                }
            }

            paths[f"{base_path}/{id_field}/navigation/{{navigationMode}}"] = {
                "get": {
                    "summary": f"{src_name}Navigation",
                    "description": "returns the navigation",
                    "tags": ["by_comid" if src == "comid" else "by_sourceid"],
                    "operationId": f"{src_name}Navigation",
                    "parameters": [
                        {"$ref": "#/components/parameters/identifier"}
                        if src == "{sourceid}"
                        else {"$ref": "#/components/parameters/comid"},
                        {"$ref": "#/components/parameters/navigationMode"},
                    ],
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/DataSourceList"  # noqa
                                    }
                                }
                            },
                        },
                        **RESPONSES,
                    },
                }
            }

            paths[f"{base_path}/{id_field}/navigation/{{navigationMode}}/{{dataSource}}"] = {
                "get": {
                    "summary": f"{src_name}NavigationDataSource",
                    "description": (
                        "returns all features found along the specified navigation as points in WGS84 lat/lon GeoJSON"
                    ),
                    "tags": ["by_comid" if src == "comid" else "by_sourceid"],
                    "operationId": f"{src_name}NavigationDataSource",
                    "parameters": [
                        {"$ref": "#/components/parameters/identifier"}
                        if src == "{sourceid}"
                        else {"$ref": "#/components/parameters/comid"},
                        {"$ref": "#/components/parameters/navigationMode"},
                        {
                            "name": "dataSource",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string", "example": "nwissite", "enum": source_names_enumerated},
                        },
                        {"$ref": "#/components/parameters/distance"},
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
                                "application/vnd.geo+json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/FeatureCollection"  # noqa
                                    }
                                },
                                "application/ld+json": {
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

            params = [
                {"$ref": "#/components/parameters/identifier"}
                if src == "{sourceid}"
                else {"$ref": "#/components/parameters/comid"},
                {"$ref": "#/components/parameters/navigationMode"},
            ]
            if src == "comid":
                params.extend(
                    [
                        {"$ref": "#/components/parameters/trimStart"},
                        {"$ref": "#/components/parameters/trimTolerance"},
                    ]
                )

            paths[f"{base_path}/{id_field}/navigation/{{navigationMode}}/flowlines"] = {
                "get": {
                    "summary": f"{src_name}NavigationFlowlines",
                    "description": ("returns the flowlines for the specified " "navigation in WGS84 lat/lon GeoJSON"),
                    "tags": ["by_comid" if src == "comid" else "by_sourceid"],
                    "operationId": f"{src_name}NavigationFlowlines",
                    "parameters": params,
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/FeatureCollection"  # noqa
                                    }
                                },
                                "application/vnd.geo+json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/FeatureCollection"  # noqa
                                    }
                                },
                                "application/ld+json": {
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
        oas["tags"] = tags
        return oas

    def __repr__(self):
        return "API(plugins=[{}])".format(", ".join(self.plugins.keys()))

    def __str__(self):
        return "API"
