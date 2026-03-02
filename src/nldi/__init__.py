#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0-1.0
# See the full copyright notice in LICENSE.md
#
"""Network Linked Data Index (NLDI) Python package."""

# __version__ = "2.3.0"

from importlib.metadata import PackageNotFoundError
from importlib.metadata import metadata as _my_metadata

## Using the lib metadata means we only need to change the version information in
## one place: the pyproject.toml.  Any virtual environment with this package installed
## should report the version string as discovered in that metadata.

try:
    project_info = _my_metadata("nldi-py")
    __version__ = project_info["Version"]
except PackageNotFoundError:
    ## Sentinal values -- allow the caller to proceed, but something is weird with the python library and/or virtual env.
    __version__ = "0.0.0"
except Exception as e:
    import logging

    logging.error(f"Unexpected error {e}")
    raise RuntimeError("Unable to continue.") from e
finally:
    del _my_metadata
