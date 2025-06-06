#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""Default values for configuration options."""

NLDI_URL = "https://127.0.0.1:80"
NLDI_PATH = "/api/nldi-py"

POSTGRES_PASSWORD = "changeMe"  # noqa: S105
NLDI_DATABASE_ADDRESS = "localhost"
NLDI_DATABASE_PORT = 5432
NLDI_DATABASE_NAME = "nldi"
NLDI_DB_OWNER_USERNAME = "nldi"
NLDI_DB_OWNER_PASSWORD = "changeMe"  # noqa: S105
NLDI_SCHEMA_OWNER_USERNAME = "nldi_schema_owner"
NLDI_SCHEMA_OWNER_PASSWORD = "changeMe"  # noqa: S105
NHDPLUS_SCHEMA_OWNER_USERNAME = "nhdplus"
NLDI_READ_ONLY_USERNAME = "read_only_user"
NLDI_READ_ONLY_PASSWORD = "changeMe"  # noqa: S105
PYGEOAPI_URL = "https://labs.waterdata.usgs.gov/api/nldi/pygeoapi"

LICENSE = {
    "name": "CC-BY 1.0 license",
    "url": "https://creativecommons.org/licenses/by/1.0/",
}

PROVIDER = {
    "name": "United States Geological Survey",
    "url": "https://labs.waterdata.usgs.gov/",
}
