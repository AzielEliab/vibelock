"""Dual-channel physical tests move the score the right way.

Directionality only — no published operating points, no magic numbers.
"""

from __future__ import annotations

from vibelock.scoring import (
    DRIFT_EXCESSIVE,
    LATENCY_OUT_OF_BOUNDS,
    analyze,
)


def _codes(result) -> set[str]:
    return set(result.reason_codes)


def test_authentic_pair_scores_higher_than_uncorrelated(authentic_pair, uncorrelated_pair):
    good = analyze(authentic_pair.audio, authentic_pair.sr, authentic_pair.vibration)
    bad = analyze(uncorrelated_pair.audio, uncorrelated_pair.sr, uncorrelated_pair.vibration)
    assert good.mode == "dual_channel"
    assert bad.mode == "dual_channel"
    assert 0.0 <= good.score <= 1.0
    assert 0.0 <= bad.score <= 1.0
    assert good.score > bad.score


def test_delayed_pair_triggers_latency_or_drift(authentic_pair, delayed_pair):
    good = analyze(authentic_pair.audio, authentic_pair.sr, authentic_pair.vibration)
    bad = analyze(delayed_pair.audio, delayed_pair.sr, delayed_pair.vibration)
    codes = _codes(bad)
    assert LATENCY_OUT_OF_BOUNDS in codes or DRIFT_EXCESSIVE in codes
    assert bad.score < good.score


def test_long_reverb_scores_lower_on_decay(authentic_pair, long_reverb):
    good = analyze(authentic_pair.audio, authentic_pair.sr)
    bad = analyze(long_reverb, authentic_pair.sr)
    dec_good = next(c.score for c in good.checks if c.name == "decay")
    dec_bad = next(c.score for c in bad.checks if c.name == "decay")
    assert dec_bad < dec_good
    assert bad.score < good.score
