"""System smoke tests — every endpoint returns expected status and content-type.

Run with: task test:system
Requires a running app (task dev) pointed at real RDS + pygeoapi.
"""

import pytest

pytestmark = pytest.mark.system


class TestLandingPage:
    def test_root(self, client):
        r = client.get("")
        assert r.status_code == 200
        body = r.json()
        assert "title" in body
        assert "links" in body

    def test_landing_page_links_resolve(self, client):
        r = client.get("")
        for link in r.json()["links"]:
            href = link["href"]
            resp = client.get(href)
            assert resp.status_code == 200, f"{href} returned {resp.status_code}"

    def test_health(self, client):
        r = client.get("about/health")
        assert r.status_code == 200
        body = r.json()
        assert body["db"]["status"] == "online"
        assert body["pygeoapi"]["status"] == "online"

    def test_openapi(self, client):
        r = client.get("docs/openapi.json")
        assert r.status_code == 200


class TestSources:
    def test_list_sources(self, client):
        r = client.get("linked-data?f=json")
        assert r.status_code == 200
        sources = r.json()
        assert isinstance(sources, list)
        assert len(sources) > 0
        assert "source" in sources[0]

    def test_list_sources_geojson(self, client):
        r = client.get("linked-data?f=json")
        sources = r.json()
        # Find a known source
        wqp = [s for s in sources if s["source"].lower() == "wqp"]
        assert len(wqp) == 1


class TestFeatures:
    def test_single_feature(self, client):
        r = client.get("linked-data/wqp/USGS-05427930?f=json")
        assert r.status_code == 200
        assert "application/geo+json" in r.headers["content-type"]
        body = r.json()
        assert body["type"] == "FeatureCollection"
        assert len(body["features"]) == 1

    def test_single_feature_jsonld(self, client):
        r = client.get("linked-data/wqp/USGS-05427930?f=jsonld")
        assert r.status_code == 200
        assert "application/ld+json" in r.headers["content-type"]
        body = r.json()
        assert "@context" in body
        assert "@id" in body

    def test_feature_not_found(self, client):
        r = client.get("linked-data/wqp/DOES-NOT-EXIST-999?f=json")
        assert r.status_code == 404

    def test_source_not_found(self, client):
        r = client.get("linked-data/nosuchsource/anything?f=json")
        assert r.status_code == 404

    def test_comid_feature(self, client):
        r = client.get("linked-data/comid/13293396?f=json")
        assert r.status_code == 200
        body = r.json()
        assert body["type"] == "FeatureCollection"


class TestNavigation:
    def test_nav_modes(self, client):
        r = client.get("linked-data/comid/13293396/navigation?f=json")
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 4  # UM, UT, DM, DD

    def test_nav_flowlines(self, client):
        r = client.get("linked-data/comid/13293396/navigation/DM/flowlines?distance=10&f=json")
        assert r.status_code == 200
        body = r.json()
        assert body["type"] == "FeatureCollection"

    def test_nav_features(self, client):
        r = client.get("linked-data/comid/13293396/navigation/DM/wqp?distance=50&f=json")
        assert r.status_code == 200
        body = r.json()
        assert body["type"] == "FeatureCollection"

    def test_nav_features_jsonld(self, client):
        r = client.get("linked-data/comid/13293396/navigation/DM/wqp?distance=50&f=jsonld")
        assert r.status_code == 200
        assert "application/ld+json" in r.headers["content-type"]

    def test_nav_from_source_feature(self, client):
        r = client.get("linked-data/wqp/USGS-05427930/navigation/DM/flowlines?distance=10&f=json")
        assert r.status_code == 200
        body = r.json()
        assert body["type"] == "FeatureCollection"


class TestBasin:
    def test_basin(self, client):
        r = client.get("linked-data/comid/13293396/basin?f=json")
        assert r.status_code == 200
        body = r.json()
        assert body["type"] == "FeatureCollection"
        assert body["features"][0]["geometry"]["type"] in ("Polygon", "MultiPolygon")

    def test_basin_simplified(self, client):
        r = client.get("linked-data/comid/13293396/basin?simplified=true&f=json")
        assert r.status_code == 200

    def test_basin_split(self, client):
        r = client.get("linked-data/wqp/USGS-05427930/basin?f=json")
        assert r.status_code == 200
        body = r.json()
        assert body["type"] == "FeatureCollection"


class TestHydrolocation:
    def test_hydrolocation(self, client):
        r = client.get("linked-data/hydrolocation?coords=POINT(-89.35 43.0883)&f=json")
        assert r.status_code == 200
        body = r.json()
        assert body["type"] == "FeatureCollection"
        assert len(body["features"]) == 2  # indexed + provided

    def test_comid_position(self, client):
        r = client.get("linked-data/comid/position?coords=POINT(-89.35 43.0883)&f=json")
        assert r.status_code == 200
        body = r.json()
        assert body["type"] == "FeatureCollection"
