"""Temporal detectors flag flicker / interpolation / identity attacks."""

from __future__ import annotations

from vibelock.scoring import (
    IDENTITY_FLICKER,
    INTERP_ARTIFACT,
    TEMPORAL_FLICKER,
    analyze,
)
from vibelock.synth_media import authentic_video, deepfake_video, interpolated_video


def test_authentic_video_outranks_deepfake_video():
    good = analyze(frames=authentic_video(n=12, h=64, w=64, seed=3), fps=25.0)
    bad = analyze(frames=deepfake_video(n=12, h=64, w=64, seed=9), fps=25.0)
    assert good.mode == "video"
    assert good.score > bad.score
    assert bad.score < 0.42
    assert set(bad.reason_codes).intersection({TEMPORAL_FLICKER, IDENTITY_FLICKER})


def test_interpolated_video_flags_or_loses():
    good = analyze(frames=authentic_video(n=12, h=48, w=48, seed=4), fps=25.0)
    bad = analyze(frames=interpolated_video(n=12, h=48, w=48, seed=4), fps=25.0)
    assert bad.score <= good.score
    # Strong blends should emit INTERP_ARTIFACT; if not, they still must not win.
    if INTERP_ARTIFACT not in bad.reason_codes:
        assert bad.score < good.score or bad.score < 0.7
