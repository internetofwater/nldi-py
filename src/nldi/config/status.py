#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#

from collections import UserDict
from typing import Literal, Optional, TypeVar

import msgspec

OnlineOffline = TypeVar("OnlineOffline", bound=Literal["online", "offline", "n/a"])


class ServiceHealth(msgspec.Struct):
    name: str
    cfg: str
    status: OnlineOffline
    msg: Optional[str] = ""


class SystemHealth(msgspec.Struct):
    server: ServiceHealth
    db: ServiceHealth
    pygeoapi: ServiceHealth


dumps = msgspec.json.Encoder().encode
