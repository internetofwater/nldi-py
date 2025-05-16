#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

"""
Test suite for nldi-py package

Most test files begin with a number.  This roughly aligns with the order
of test running. Within the test file, a decorator (``pytest.order()``)
sets the order of test execution.  The number there should be in the range
of the 2-digit number of the file itself.  This is a crude way to enforce ordering
and organization.


"""

# prefix for the API under test
API_PREFIX = "/api/nldi"

# Prefix for the authoritative source API providing "expected" answers to API requests.
# This is the service we are trying to copy.
AUTH_PREFIX = "https://nhgf.dev-wma.chs.usgs.gov/api/nldi"


# ## The sequence of endpoints that we need to offer and where they are tested:

# - 30_sys_routes.py
#    - f"{API_PREFIX}/openapi"
#    - f"{API_PREFIX}/about/info"
#    - f"{API_PREFIX}/about/config"
#    - f"{API_PREFIX}/about/health"

# - 40_crawlersources_test.py
#   - f"{API_PREFIX}/linked-data"

# - 50_flowline_test.py
#   - f"{API_PREFIX}/linked-data/comid/{comid}"
#   - f"{API_PREFIX}/linked-data/comid/position?{coords}"

# - 60_features_test.py
#   - f"{API_PREFIX}/linked-data/{source_name}"
#   - f"{API_PREFIX}/linked-data/{source_name}/{identifier}"
#   - f"{API_PREFIX}/linked-data/{source_name}/{identifier}/basin"

# - 70_navigation_test.py
#   - f"{API_PREFIX}/linked-data/{source_name}/{identifier}/navigation"
#   - f"{API_PREFIX}/linked-data/{source_name}/{identifier}/navigation/{nav_mode}"
#   - f"{API_PREFIX}/linked-data/{source_name}/{identifier}/navigation/{nav_mode}/flowlines"
#   - f"{API_PREFIX}/linked-data/{source_name}/{identifier}/navigation/{nav_mode}/{data_source}"

# - 80_misc_routes_test.py
#   - f"{API_PREFIX}/"
#   - f"{API_PREFIX}/linked-data/hydrolocation?{coords}"
