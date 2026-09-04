"""Pitch / phase-shift attacks lower the audio-only score."""

from __future__ import annotations

from vibelock.scoring import PITCH_JUMP, PITCH_OVERFLAT, PHASE_SHIFT_UNNATURAL, analyze
from vibelock.synth_media import phase_stretched, pitch_flat, pitch_jumped


def test_pitch_jump_and_flat_lower_score(authentic_pair):
    good = analyze(authentic_pair.audio, authentic_pair.sr)
    jumped = analyze(pitch_jumped(authentic_pair.audio, authentic_pair.sr), authentic_pair.sr)
    flat = analyze(pitch_flat(duration_s=1.0, sr=authentic_pair.sr), authentic_pair.sr)
    assert jumped.score < good.score
    assert flat.score < good.score
    codes = set(jumped.reason_codes) | set(flat.reason_codes)
    assert codes.intersection({PITCH_JUMP, PITCH_OVERFLAT})


def test_phase_stretch_lowers_or_codes(authentic_pair):
    good = analyze(authentic_pair.audio, authentic_pair.sr)
    bad = analyze(phase_stretched(authentic_pair.audio, authentic_pair.sr), authentic_pair.sr)
    assert bad.score < good.score
    assert PHASE_SHIFT_UNNATURAL in bad.reason_codes or bad.score < good.score - 0.02
