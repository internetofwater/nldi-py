#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0-1.0
#


import json
from collections.abc import AsyncGenerator

import pytest

from nldi import util


@pytest.mark.order(3)
@pytest.mark.unittest
async def test_async_stream_j2_template_produces_feature_collection():
    """Our templating function must produce a valid GeoJSON FeatureCollection from an async generator."""

    async def sample_features() -> AsyncGenerator[dict, None]:
        """Dummy async generator; mimics a database call that yields items asynchronously via async generator"""
        yield {"type": "Feature", "id": 1, "geometry": None, "properties": {"name": "a"}}
        yield {"type": "Feature", "id": 2, "geometry": None, "properties": {"name": "b"}}

    chunks = []
    async for chunk in util.async_stream_j2_template("FeatureCollection.j2", sample_features()):
        chunks.append(chunk)

    parsed = json.loads("".join(chunks))

    assert parsed["type"] == "FeatureCollection"
    assert len(parsed["features"]) == 2
    assert parsed["features"][0]["id"] == 1
