#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""Base data structures to read in config information."""

import logging
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Self

import httpx
import sqlalchemy as sa
from sqlalchemy.engine import URL as DB_URL

from .. import __version__, util
from . import default, status
from ._yaml import load_yaml


@dataclass
class ServerConfig:
    url: str
    prefix: str
    pygeoapi_url: str

    @property
    def base_url(self) -> str:
        return util.url_join(self.url, self.prefix)

    def ping(self, subservice: str | None = None) -> bool:
        if subservice == "pygeoapi":
            _uri = util.url_join(self.pygeoapi_url, "processes?f=json")
            r = httpx.get(_uri, timeout=5, verify=False)  # noqa: S501
            return r.status_code == 200
        return True

    def healthstatus(self, subservice: str | None = None) -> status.ServiceHealth:
        if subservice == "pygeoapi":
            return status.ServiceHealth(
                name="pygeoapi",
                cfg=str(self.pygeoapi_url),
                status="online" if self.ping("pygeoapi") else "offline",
            )
        return status.ServiceHealth(
            name=f"NLDI {__version__}",
            cfg=str(self.base_url),
            status="online",
        )


@dataclass
class DatabaseConfig:
    host: str
    port: int
    dbname: str
    user: str
    password: str

    @property
    def URL(self) -> DB_URL:  # noqa: N802
        return DB_URL.create(
            "postgresql+psycopg",
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.dbname,
        )

    def ping(self) -> bool:
        healthy = False  # pessimistic default
        try:
            _private_engine = sa.create_engine(
                self.URL,
                pool_pre_ping=True,
                connect_args={"connect_timeout": 3},
            )
            with _private_engine.connect() as connection:
                result = connection.execute(sa.select(1))
            if not result:
                raise sa.exc.SQLAlchemyError
            _private_engine.dispose()
        except (ModuleNotFoundError, sa.exc.NoSuchModuleError) as e:
            logging.warning(f"Cannot load the dialect/driver module: {e}")
        except sa.exc.DBAPIError as e:
            logging.warning(f"Error Connecting to the Database: {e}.")
        except sa.exc.SQLAlchemyError as e:
            logging.warning(f"Couldn't run SELECT: {e}")
        else:
            healthy = True
        finally:
            logging.info("Database is %s", "alive" if healthy else "dead")
        return healthy

    def healthstatus(self) -> status.ServiceHealth:
        return status.ServiceHealth(
            name="db",
            cfg=str(self.URL),
            status="online" if self.ping() else "offline",
        )


@dataclass
class MetadataConfig:
    title: str
    description: str
    keywords: list[str]
    terms_of_service: str
    license: dict[str, str]
    provider: dict[str, str]


@dataclass
class MasterConfig:
    server: ServerConfig
    db: DatabaseConfig
    metadata: MetadataConfig

    @classmethod
    def clean_dict(cls, d: dict) -> dict:
        cleaned = {}
        for key, value in d.items():
            if value is not None:
                if isinstance(value, dict):
                    subdict = cls.clean_dict(value)
                    if subdict:
                        cleaned[key] = subdict
                else:
                    cleaned[key] = value
        return cleaned

    @classmethod
    def from_yaml(cls, input: Any) -> Self:
        try:
            cfg = load_yaml(input)
        except OSError as e:
            logging.error("Unable to load configuration: %s", e)
            raise
        serv_section = cls.clean_dict(cfg["server"])
        if serv_section.get("data") is None:
            serv_section["data"] = {}

        md_id_section = cls.clean_dict(cfg["metadata"]["identification"])
        try:
            pygeoapi_cfg = cfg.get("pygeoapi")
            pygeoapi_url = pygeoapi_cfg.get("gdp_url",  default.PYGEOAPI_URL) or default.PYGEOAPI_URL
        except (AttributeError, KeyError):
            logging.warning(f"Unable to determine pygeoapi url.  Using default: {default.PYGEOAPI_URL}")
            pygeoapi_url = default.PYGEOAPI_URL

        return cls(
            server=ServerConfig(
                url=serv_section.get("url", default.NLDI_URL),
                prefix=serv_section.get("prefix", default.NLDI_PATH),
                pygeoapi_url=pygeoapi_url.rstrip("/"),
            ),
            db=DatabaseConfig(
                host=serv_section["data"].get("host", default.NLDI_DATABASE_ADDRESS),
                port=serv_section["data"].get("port", default.NLDI_DATABASE_PORT),
                dbname=serv_section["data"].get("dbname", default.NLDI_DATABASE_NAME),
                user=serv_section["data"].get("user", default.NLDI_DB_OWNER_USERNAME),
                password=serv_section["data"].get("password", default.NLDI_DB_OWNER_PASSWORD),
            ),
            metadata=MetadataConfig(
                title=md_id_section.get("title", "TITLE"),
                description=md_id_section.get("description", "DESCRIPTION").replace("\n", " "),
                keywords=md_id_section.get("keywords", ["nldi"]),
                terms_of_service=md_id_section.get("terms_of_service", "CC0"),
                license=md_id_section.get("license", default.LICENSE),
                provider=md_id_section.get("provider", default.PROVIDER),
            ),
        )
