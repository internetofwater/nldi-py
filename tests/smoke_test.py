#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

"""
'Smoke' Test -- When you plug it in, does it smoke and catch fire?

Smoke tests merely verify that the infrastructure is intact. Once
later tests are up, these become largely unnecessary, as later
function presumes successful import, etc.
"""

import nldi
import pytest


@pytest.mark.order(0)
@pytest.mark.unittest
def test_successful_import() -> None:
    """Does the module import at all?"""
    assert nldi.__version__ is not None


@pytest.mark.order(1)
@pytest.mark.unittest
def test_fixtures_present(runner) -> None:
    """Verify the CLI fixture is available."""
    assert runner is not None
