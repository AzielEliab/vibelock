"""Shared synthetic fixtures. No hardware, no recorded speech."""

from __future__ import annotations

import pytest

from tests.helpers import SR
from vibelock.synth import DualPair, make_pair


@pytest.fixture(scope="session")
def sr() -> int:
    return SR


@pytest.fixture(scope="session")
def authentic_pair() -> DualPair:
    return make_pair(duration_s=1.2, sr=SR, f0=120.0, seed=20260701)
