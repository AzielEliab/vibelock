"""Spatial detectors move the score the right way on synthetic stills."""

from __future__ import annotations

from vibelock.scoring import (
    BLEND_BOUNDARY,
    CHROMA_INCONSISTENT,
    FREQ_FINGERPRINT,
    NOISE_INCONSISTENT,
    analyze,
)
from vibelock.synth_media import authentic_image, deepfake_image
from vibelock.vision import analyze_image


def test_authentic_image_outranks_deepfake():
    good = analyze(image=authentic_image(96, 96, seed=2))
    bad = analyze(image=deepfake_image(96, 96, seed=8))
    assert good.mode == "image"
    assert bad.mode == "image"
    assert good.score > bad.score
    assert bad.score < 0.45
    assert bad.reason_codes


def test_deepfake_image_emits_spatial_codes():
    checks = analyze_image(deepfake_image(96, 96, seed=11))
    codes = {c.reason_code for c in checks if c.reason_code}
    assert codes.intersection(
        {FREQ_FINGERPRINT, NOISE_INCONSISTENT, BLEND_BOUNDARY, CHROMA_INCONSISTENT}
    )


def test_image_result_has_no_pixels():
    blob = analyze(image=authentic_image(48, 48, seed=1)).to_dict()
    assert "image" not in blob
    assert "frames" not in blob
    assert blob["signals"] == ["spatial"]
