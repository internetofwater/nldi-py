#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""Custom exceptions for api module."""


class ProviderGenericError(Exception):
    """provider generic error"""

    pass


class ProviderConnectionError(ProviderGenericError):
    """provider connection error"""

    pass


class ProviderTypeError(ProviderGenericError):
    """provider type error"""

    pass


class ProviderInvalidQueryError(ProviderGenericError):
    """provider invalid query error"""

    pass


class ProviderQueryError(ProviderGenericError):
    """provider query error"""

    pass


class ProviderItemNotFoundError(ProviderGenericError):
    """provider item not found query error"""

    pass
