#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#
"""
Custom exceptions for the NLDI handlers.

TODO: would like to rename these to include NLDI in the name, to distinguish from any possible name collisions.
"""


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
