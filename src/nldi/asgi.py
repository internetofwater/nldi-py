#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""An ASGI wrapper for the WSGI "standard" APP."""

from asgiref.wsgi import WsgiToAsgi

from .wsgi import APP as _APP

APP = WsgiToAsgi(_APP)
