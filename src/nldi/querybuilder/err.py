#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
#
"""Exceptions for the NLDI Query Builder"""


class FunctionGenericError(Exception):
    """function generic error"""

    pass


class FunctionConnectionError(FunctionGenericError):
    """function connection error"""

    pass


class FunctionTypeError(FunctionGenericError):
    """function type error"""

    pass


class FunctionInvalidQueryError(FunctionGenericError):
    """function invalid query error"""

    pass


class FunctionQueryError(FunctionGenericError):
    """function query error"""

    pass


class FunctionItemNotFoundError(FunctionGenericError):
    """function item not found query error"""

    pass
