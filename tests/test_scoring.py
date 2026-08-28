"""Scoring combines checks and emits reason codes without retaining audio."""

from __future__ import annotations

from vibelock.scoring import (
    CheckResult,
    analyze,
    clip01,
    combine,
    logistic_score,
)


def test_clip01():
    assert clip01(-1.0) == 0.0
    assert clip01(2.0) == 1.0
    assert clip01(0.3) == 0.3


def test_logistic_score_direction():
    assert logistic_score(0.6, good=0.6, bad=0.1) > logistic_score(0.1, good=0.6, bad=0.1)
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
    blob = result.to_dict()
    assert "score" in blob and "reason_codes" in blob
    assert "audio" not in blob
    assert "vibration" not in blob
    assert "waveform" not in blob


def test_analyze_json_has_no_waveform(authentic_pair):
    result = analyze(authentic_pair.audio, authentic_pair.sr, authentic_pair.vibration)
    blob = result.to_dict()
    assert set(blob.keys()) >= {"score", "mode", "reason_codes", "checks"}
    for key in blob:
        assert key not in {"audio", "vibration", "waveform", "pcm"}


def test_uncorrelated_dual_scores_below_authentic(authentic_pair, uncorrelated_pair):
    good = analyze(authentic_pair.audio, authentic_pair.sr, authentic_pair.vibration)
    bad = analyze(uncorrelated_pair.audio, uncorrelated_pair.sr, uncorrelated_pair.vibration)
    assert good.score > bad.score
    assert 0.0 <= bad.score <= 1.0
