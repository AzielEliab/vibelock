"""Scoring combines checks and emits reason codes without retaining audio."""

from __future__ import annotations

from vibelock.scoring import (
    CheckResult,
    clip01,
    combine,
    logistic_score,
    analyze,
)
from tests.helpers import uncorrelated_pair


def test_clip01():
    assert clip01(-1.0) == 0.0
    assert clip01(2.0) == 1.0
    assert clip01(0.3) == 0.3


def test_logistic_score_direction():
    assert logistic_score(0.6, good=0.6, bad=0.1) > 0.9
    assert logistic_score(0.1, good=0.6, bad=0.1) < 0.1
    assert logistic_score(0.35, good=0.6, bad=0.1) > logistic_score(0.2, good=0.6, bad=0.1)


def test_combine_emits_unique_reason_codes():
    checks = [
        CheckResult("coherence", 0.2, "COHERENCE_LOW", {}),
        CheckResult("transfer", 0.2, "COHERENCE_LOW", {}),
        CheckResult("decay", 0.8, None, {}),
    ]
    result = combine(checks, "dual_channel", sample_rate=16000, n_samples=100)
    assert result.reason_codes.count("COHERENCE_LOW") == 1
    assert 0.0 <= result.score <= 1.0
    d = result.to_dict()
    assert "score" in d and "reason_codes" in d
    # Privacy: no waveform keys.
    assert "audio" not in d
    assert "samples" not in d or d["n_samples"] == 100


def test_analyze_json_has_no_waveform(authentic_pair):
    result = analyze(authentic_pair.audio, authentic_pair.sr, authentic_pair.vibration)
    blob = result.to_dict()
    assert set(blob.keys()) >= {"score", "mode", "reason_codes", "checks"}
    for key in blob:
        assert key not in {"audio", "vibration", "waveform", "pcm"}


def test_dual_score_below_audio_only_when_vibration_is_fake(authentic_pair):
    """A nonsense vibration channel should not raise the score vs audio-only."""
    audio_only = analyze(authentic_pair.audio, authentic_pair.sr, vibration=None)
    fake = uncorrelated_pair(authentic_pair.sr)
    dual = analyze(authentic_pair.audio, authentic_pair.sr, fake.vibration)
    assert dual.mode == "dual_channel"
    assert dual.score < audio_only.score or "COHERENCE_LOW" in dual.reason_codes
