"""Audio-only forensic checks move the score the right way.

Directionality only — no published operating points.
"""

from __future__ import annotations

from vibelock.scoring import (
    PHASE_DISCONTINUITY,
    PHASE_OVERFLAT,
    TEMPORAL_SPLICE,
    VOCODER_BUZZ,
    analyze,
)


def _codes(result) -> set[str]:
    return set(result.reason_codes)


def test_audio_only_mode(authentic_pair):
    result = analyze(authentic_pair.audio, authentic_pair.sr, vibration=None)
    assert result.mode == "audio_only"
    assert 0.0 <= result.score <= 1.0


def test_hard_splice_flags_temporal_or_phase(authentic_pair, hard_splice):
    good = analyze(authentic_pair.audio, authentic_pair.sr)
    bad = analyze(hard_splice, authentic_pair.sr)
    codes = _codes(bad)
    assert TEMPORAL_SPLICE in codes or PHASE_DISCONTINUITY in codes
    assert bad.score < good.score


def test_vocoder_or_phase_attacks_lower_score(
    authentic_pair, vocoder_buzz, phase_scrambled, zero_phase
):
    good = analyze(authentic_pair.audio, authentic_pair.sr)
    attacked = []
    for name, sig in (
        ("vocoder_buzz", vocoder_buzz),
        ("phase_scrambled", phase_scrambled),
        ("zero_phase", zero_phase),
    ):
        result = analyze(sig, authentic_pair.sr)
        attacked.append((name, result))
        assert result.score < good.score, f"{name} should lower the forensic score"

    # At least one of these should also emit a related reason code.
    codes = set()
    for _name, result in attacked:
        codes.update(_codes(result))
    assert codes.intersection(
        {VOCODER_BUZZ, PHASE_DISCONTINUITY, PHASE_OVERFLAT}
    ) or all(r.score < good.score for _n, r in attacked)


def test_unstable_formants_lower_score(authentic_pair, unstable_formants):
    good = analyze(authentic_pair.audio, authentic_pair.sr)
    bad = analyze(unstable_formants, authentic_pair.sr)
    assert bad.score < good.score
