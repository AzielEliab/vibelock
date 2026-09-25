"""Experimental linguistic proxies. No speech-to-text, no accuracy claim."""

from __future__ import annotations

import numpy as np

from vibelock.linguistics import MIN_DURATION_S, analyze_linguistics
from vibelock.scoring import (
    LINGUISTIC_RHYTHM_METRONOME,
    LINGUISTIC_TRANSITION_FROZEN,
    analyze,
)


def _metronome(sr: int = 16000, seconds: float = 1.2) -> np.ndarray:
    n = int(seconds * sr)
    t = np.arange(n, dtype=np.float64) / sr
    carrier = np.sin(2.0 * np.pi * 140.0 * t)
    am = 0.5 * (1.0 + np.sin(2.0 * np.pi * 5.0 * t))
    return carrier * am


def _tone(sr: int = 16000, seconds: float = 1.0) -> np.ndarray:
    n = int(seconds * sr)
    t = np.arange(n, dtype=np.float64) / sr
    return 0.4 * np.sin(2.0 * np.pi * 180.0 * t)


def test_short_clip_is_insufficient() -> None:
    sr = 16000
    audio = _tone(sr, seconds=MIN_DURATION_S * 0.5)
    checks, meta = analyze_linguistics(audio, sr)
    assert checks == []
    assert meta["status"] == "insufficient"
    assert "experimental" in meta["note"].lower() or "Experimental" in meta["note"]


def test_metronome_fires_rhythm_code() -> None:
    sr = 16000
    checks, meta = analyze_linguistics(_metronome(sr), sr)
    assert meta["status"] == "fired"
    assert meta["evidence"] == "experimental"
    codes = {c.reason_code for c in checks}
    assert LINGUISTIC_RHYTHM_METRONOME in codes
    rhythm = next(c for c in checks if c.name == "syllable_rhythm")
    assert "not speech-to-text" in rhythm.note


def test_steady_tone_can_flag_frozen_transition() -> None:
    checks, meta = analyze_linguistics(_tone(), 16000)
    assert meta["status"] == "fired"
    codes = {c.reason_code for c in checks}
    assert LINGUISTIC_TRANSITION_FROZEN in codes


def test_authentic_speech_does_not_take_metronome_code(authentic_pair) -> None:
    checks, meta = analyze_linguistics(authentic_pair.audio, authentic_pair.sr)
    assert meta["status"] == "fired"
    codes = {c.reason_code for c in checks if c.reason_code}
    assert LINGUISTIC_RHYTHM_METRONOME not in codes
    result = analyze(authentic_pair.audio, authentic_pair.sr)
    ling = next(c for c in result.channels if c.name == "linguistics")
    assert ling.status == "fired"
    assert ling.evidence == "experimental"
    assert "accuracy" not in result.to_dict()
