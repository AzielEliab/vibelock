"""Dual-channel physical tests move the score the right way."""

from __future__ import annotations

import numpy as np

from vibelock.scoring import (
    COHERENCE_LOW,
    DECAY_IMPLAUSIBLE,
    LATENCY_OUT_OF_BOUNDS,
    TRANSFER_RESIDUAL_HIGH,
    analyze,
)
from tests.helpers import delayed_pair, long_reverb, uncorrelated_pair


def _codes(result) -> set[str]:
    return set(result.reason_codes)


def test_authentic_pair_scores_higher_than_uncorrelated(authentic_pair):
    good = analyze(authentic_pair.audio, authentic_pair.sr, authentic_pair.vibration)
    bad_pair = uncorrelated_pair(authentic_pair.sr)
    bad = analyze(bad_pair.audio, bad_pair.sr, bad_pair.vibration)
    assert good.mode == "dual_channel"
    assert 0.0 <= good.score <= 1.0
    assert 0.0 <= bad.score <= 1.0
    assert bad.score < good.score
    assert COHERENCE_LOW in _codes(bad)


def test_coherence_low_on_independent_channels(authentic_pair):
    good = analyze(authentic_pair.audio, authentic_pair.sr, authentic_pair.vibration)
    noise = np.random.default_rng(0).normal(0, 1, authentic_pair.vibration.size)
    bad = analyze(authentic_pair.audio, authentic_pair.sr, noise)
    assert COHERENCE_LOW in _codes(bad)
    assert bad.score < good.score
    coh_good = next(c.score for c in good.checks if c.name == "coherence")
    coh_bad = next(c.score for c in bad.checks if c.name == "coherence")
    assert coh_bad < coh_good


def test_transfer_residual_high_on_mismatched_pair(authentic_pair):
    good = analyze(authentic_pair.audio, authentic_pair.sr, authentic_pair.vibration)
    other = uncorrelated_pair(authentic_pair.sr)
    bad = analyze(other.audio, other.sr, other.vibration)
    assert TRANSFER_RESIDUAL_HIGH in _codes(bad)
    tr_good = next(c.score for c in good.checks if c.name == "transfer")
    tr_bad = next(c.score for c in bad.checks if c.name == "transfer")
    assert tr_bad < tr_good
    assert bad.score < good.score


def test_latency_out_of_bounds_on_large_delay(authentic_pair):
    good = analyze(authentic_pair.audio, authentic_pair.sr, authentic_pair.vibration)
    delayed = delayed_pair(authentic_pair, delay_s=0.08)
    bad = analyze(delayed.audio, delayed.sr, delayed.vibration)
    assert LATENCY_OUT_OF_BOUNDS in _codes(bad)
    assert bad.score < good.score
    lat_good = next(c.score for c in good.checks if c.name == "phase_latency")
    lat_bad = next(c.score for c in bad.checks if c.name == "phase_latency")
    assert lat_bad < lat_good


def test_decay_implausible_on_long_reverb(authentic_pair):
    good = analyze(authentic_pair.audio, authentic_pair.sr, authentic_pair.vibration)
    wet = long_reverb(authentic_pair.audio, authentic_pair.sr, tau_s=0.30)
    # Keep vibration aligned with the dry source; pad to wet length.
    pad = wet.size - authentic_pair.vibration.size
    vib = np.concatenate([authentic_pair.vibration, np.zeros(max(pad, 0))])[: wet.size]
    bad = analyze(wet, authentic_pair.sr, vib)
    assert DECAY_IMPLAUSIBLE in _codes(bad)
    dec_good = next(c.score for c in good.checks if c.name == "decay")
    dec_bad = next(c.score for c in bad.checks if c.name == "decay")
    assert dec_bad < dec_good
    assert bad.score < good.score


def test_authentic_pair_does_not_flag_coherence(authentic_pair):
    result = analyze(authentic_pair.audio, authentic_pair.sr, authentic_pair.vibration)
    assert COHERENCE_LOW not in _codes(result)
    coh = next(c for c in result.checks if c.name == "coherence")
    assert coh.score > 0.5
