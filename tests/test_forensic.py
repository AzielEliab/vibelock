"""Audio-only forensic checks move the score the right way."""

from __future__ import annotations

from vibelock.scoring import (
    DECAY_IMPLAUSIBLE,
    FORMANT_UNSTABLE,
    PHASE_DISCONTINUITY,
    TEMPORAL_SPLICE,
    VOCODER_BUZZ,
    analyze,
)
from tests.helpers import (
    hard_splice,
    long_reverb,
    phase_scrambled,
    unstable_formants,
    vocoder_buzz,
)


def _codes(result) -> set[str]:
    return set(result.reason_codes)


def test_audio_only_mode(authentic_pair):
    result = analyze(authentic_pair.audio, authentic_pair.sr, vibration=None)
    assert result.mode == "audio_only"
    assert 0.0 <= result.score <= 1.0


def test_phase_discontinuity_lowers_score(authentic_pair):
    good = analyze(authentic_pair.audio, authentic_pair.sr)
    scrambled = phase_scrambled(authentic_pair.audio, authentic_pair.sr)
    bad = analyze(scrambled, authentic_pair.sr)
    assert PHASE_DISCONTINUITY in _codes(bad)
    ph_good = next(c.score for c in good.checks if c.name == "phase_continuity")
    ph_bad = next(c.score for c in bad.checks if c.name == "phase_continuity")
    assert ph_bad < ph_good
    assert bad.score < good.score


def test_formant_unstable_lowers_score(authentic_pair):
    good = analyze(authentic_pair.audio, authentic_pair.sr)
    jumpy = unstable_formants(authentic_pair.sr)
    bad = analyze(jumpy, authentic_pair.sr)
    assert FORMANT_UNSTABLE in _codes(bad)
    f_good = next(c.score for c in good.checks if c.name == "formant")
    f_bad = next(c.score for c in bad.checks if c.name == "formant")
    assert f_bad < f_good
    assert bad.score < good.score


def test_temporal_splice_lowers_score(authentic_pair):
    good = analyze(authentic_pair.audio, authentic_pair.sr)
    spliced = hard_splice(authentic_pair.sr)
    bad = analyze(spliced, authentic_pair.sr)
    assert TEMPORAL_SPLICE in _codes(bad)
    t_good = next(c.score for c in good.checks if c.name == "temporal")
    t_bad = next(c.score for c in bad.checks if c.name == "temporal")
    assert t_bad < t_good
    assert bad.score < good.score


def test_decay_implausible_audio_only(authentic_pair):
    good = analyze(authentic_pair.audio, authentic_pair.sr)
    wet = long_reverb(authentic_pair.audio, authentic_pair.sr, tau_s=0.32)
    bad = analyze(wet, authentic_pair.sr)
    assert DECAY_IMPLAUSIBLE in _codes(bad)
    d_good = next(c.score for c in good.checks if c.name == "decay")
    d_bad = next(c.score for c in bad.checks if c.name == "decay")
    assert d_bad < d_good
    assert bad.score < good.score


def test_vocoder_buzz_lowers_buzz_score(authentic_pair):
    good = analyze(authentic_pair.audio, authentic_pair.sr)
    buzzy = vocoder_buzz(authentic_pair.audio, authentic_pair.sr, hop_hz=100.0)
    bad = analyze(buzzy, authentic_pair.sr)
    assert VOCODER_BUZZ in _codes(bad)
    g = next(c.score for c in good.checks if c.name == "buzz")
    b = next(c.score for c in bad.checks if c.name == "buzz")
    assert b < g
    assert bad.score < good.score
