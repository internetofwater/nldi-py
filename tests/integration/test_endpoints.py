"""Integration tests via TestClient — full stack through real DB.

Exercises route → DI → handler → repo → real DB → response.
Catches interface mismatches that unit tests with fakes miss.
"""

import pytest


@pytest.mark.integration
class TestEndpointIntegration:
    def test_list_sources(self, app_client):
        r = app_client.get("/api/nldi/linked-data?f=json")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)
        assert len(body) > 0
        assert "source" in body[0]

    def test_single_feature_by_comid(self, app_client):
        r = app_client.get("/api/nldi/linked-data/comid/13293396?f=json")
        assert r.status_code == 200
        body = r.json()
        assert body["type"] == "FeatureCollection"
        assert len(body["features"]) == 1

    def test_single_feature_by_source(self, app_client):
        r = app_client.get("/api/nldi/linked-data/wqp/USGS-05427930?f=json")
        assert r.status_code == 200
        body = r.json()
        assert body["type"] == "FeatureCollection"

    def test_comid_position(self, app_client):
        r = app_client.get("/api/nldi/linked-data/comid/position?coords=POINT(-89.4423056 43.1402778)&f=json")
        assert r.status_code == 200
        body = r.json()
        assert body["type"] == "FeatureCollection"

    def test_comid_position_not_found(self, app_client):
        r = app_client.get("/api/nldi/linked-data/comid/position?coords=POINT(0 0)&f=json")
        assert r.status_code == 404

    def test_comid_position_malformed_coords(self, app_client):
        r = app_client.get("/api/nldi/linked-data/comid/position?coords=POINT&f=json")
        assert r.status_code == 400

    def test_nav_modes(self, app_client):
        r = app_client.get("/api/nldi/linked-data/comid/13293396/navigation?f=json")
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 4

    def test_nav_flowlines(self, app_client):
        r = app_client.get("/api/nldi/linked-data/comid/13293396/navigation/DM/flowlines?distance=10&f=json")
        assert r.status_code == 200
        body = r.json()
        assert body["type"] == "FeatureCollection"

    def test_nav_features(self, app_client):
        r = app_client.get("/api/nldi/linked-data/comid/13293396/navigation/DM/wqp?distance=50&f=json")
        assert r.status_code == 200
        body = r.json()
        assert body["type"] == "FeatureCollection"

    def test_nav_from_source_feature(self, app_client):
        r = app_client.get("/api/nldi/linked-data/wqp/USGS-05427930/navigation/DM/flowlines?distance=10&f=json")
        assert r.status_code == 200
        body = r.json()
        assert body["type"] == "FeatureCollection"

    def test_list_features_by_source(self, app_client):
        r = app_client.get("/api/nldi/linked-data/wqp?f=json")
        assert r.status_code == 200
        body = r.json()
        assert body["type"] == "FeatureCollection"
        assert len(body["features"]) > 0

    def test_list_comids_with_pagination(self, app_client):
        r = app_client.get("/api/nldi/linked-data/comid?limit=10&offset=10&f=json")
        assert r.status_code == 200
        body = r.json()
        assert body["type"] == "FeatureCollection"
        assert len(body["features"]) == 10

    def test_basin(self, app_client):
        r = app_client.get("/api/nldi/linked-data/comid/13293396/basin?f=json")
        assert r.status_code == 200
        body = r.json()
        assert body["type"] == "FeatureCollection"

    def test_feature_not_found(self, app_client):
        r = app_client.get("/api/nldi/linked-data/wqp/DOES-NOT-EXIST?f=json")
        assert r.status_code == 404

    def test_source_not_found(self, app_client):
        r = app_client.get("/api/nldi/linked-data/nosuchsource/anything?f=json")
        assert r.status_code == 404

    def test_jsonld(self, app_client):
        r = app_client.get("/api/nldi/linked-data/wqp/USGS-05427930?f=jsonld")
        assert r.status_code == 200
        assert "application/ld+json" in r.headers["content-type"]
        body = r.json()
        assert "@context" in body

    def test_health_pool_stats(self, app_client):
        r = app_client.get("/api/nldi/about/health")
        assert r.status_code == 200
        body = r.json()
        pool = body["db"]["pool"]
        assert "size" in pool
        assert "checked_in" in pool
        assert "checked_out" in pool
        assert "overflow" in pool
