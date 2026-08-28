"""Shared synthetic fixtures. No hardware, no recorded speech.

Seeds live in tests/helpers.py so the suite stays deterministic.
Fixtures wrap those generators so tests can request them by name.
"""

from __future__ import annotations

import numpy as np
import pytest

from tests.helpers import (
    SR,
    delayed_pair as _delayed_pair,
    hard_splice as _hard_splice,
    long_reverb as _long_reverb,
    phase_scrambled as _phase_scrambled,
    uncorrelated_pair as _uncorrelated_pair,
    unstable_formants as _unstable_formants,
    vocoder_buzz as _vocoder_buzz,
    zero_phase as _zero_phase,
)
from vibelock.synth import DualPair, make_pair


@pytest.fixture(scope="session")
def sr() -> int:
    return SR


@pytest.fixture(scope="session")
def authentic_pair() -> DualPair:
    return make_pair(duration_s=1.2, sr=SR, f0=120.0, seed=20260701)


@pytest.fixture(scope="session")
def uncorrelated_pair() -> DualPair:
    return _uncorrelated_pair(SR)


@pytest.fixture(scope="session")
def delayed_pair(authentic_pair: DualPair) -> DualPair:
    """Authentic pair with an 80 ms air-channel delay (out of bounds)."""
    return _delayed_pair(authentic_pair, delay_s=0.08)


@pytest.fixture(scope="session")
def long_reverb(authentic_pair: DualPair) -> np.ndarray:
    return _long_reverb(authentic_pair.audio, authentic_pair.sr, tau_s=0.30)


@pytest.fixture(scope="session")
def phase_scrambled(authentic_pair: DualPair) -> np.ndarray:
    return _phase_scrambled(authentic_pair.audio, authentic_pair.sr)


@pytest.fixture(scope="session")
def zero_phase(authentic_pair: DualPair) -> np.ndarray:
    return _zero_phase(authentic_pair.audio, authentic_pair.sr)


@pytest.fixture(scope="session")
def hard_splice() -> np.ndarray:
    return _hard_splice(SR)


@pytest.fixture(scope="session")
def unstable_formants() -> np.ndarray:
    return _unstable_formants(SR)


@pytest.fixture(scope="session")
def vocoder_buzz(authentic_pair: DualPair) -> np.ndarray:
    return _vocoder_buzz(authentic_pair.audio, authentic_pair.sr, hop_hz=100.0)
