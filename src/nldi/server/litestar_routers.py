#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""Routes served by this app."""

from litestar.types import ControllerRouterHandler

from ..domain.about.controllers import AboutController
from ..domain.linked_data.controllers import LinkedDataController
from ..domain.root.controllers import RootController

route_handlers: list[ControllerRouterHandler] = [
    RootController,
    AboutController,
    LinkedDataController,
]
