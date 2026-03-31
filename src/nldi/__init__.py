# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""NLDI — Network Linked Data Index."""

from importlib.metadata import PackageNotFoundError, metadata

try:
    __version__ = metadata("nldi-py")["Version"]
except PackageNotFoundError:
    __version__ = "0.0.0"
