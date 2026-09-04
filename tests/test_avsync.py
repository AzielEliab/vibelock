"""Talking-head A/V coupling: authentic envelope drives motion; deepfake does not."""

from __future__ import annotations

from vibelock.scoring import AV_SYNC_FAIL, analyze
from vibelock.synth_media import authentic_av, deepfake_av


def test_authentic_av_outranks_desynced():
    good = authentic_av(duration_s=0.48, seed=5)
    bad = deepfake_av(duration_s=0.48, seed=11)
    g = analyze(good.audio, good.sr, frames=good.frames, fps=good.fps)
    b = analyze(bad.audio, bad.sr, frames=bad.frames, fps=bad.fps)
    assert g.mode == "av"
    assert b.mode == "av"
    assert g.score > b.score
    assert b.score < 0.42
    assert AV_SYNC_FAIL in b.reason_codes or b.verdict == "deepfake"
    assert "av_sync" in g.signals
