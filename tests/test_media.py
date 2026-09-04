"""PNG / PPM / VLVD round-trips. No network."""

from __future__ import annotations

import numpy as np

from vibelock.media import (
    decode_image_bytes,
    decode_png,
    decode_ppm,
    decode_vlvd,
    encode_png,
    encode_ppm,
    encode_vlvd,
    sniff_media,
)
from vibelock.synth_media import authentic_image, authentic_video


def test_png_roundtrip_mae():
    img = authentic_image(40, 48, seed=4)
    raw = encode_png(img)
    assert sniff_media(raw, "x.png") == "image"
    got = decode_png(raw)
    assert got.shape == img.shape
    assert float(np.mean(np.abs(got - img))) < 0.02


def test_ppm_roundtrip():
    img = authentic_image(32, 32, seed=1)
    raw = encode_ppm(img)
    assert sniff_media(raw, "x.ppm") == "image"
    got = decode_ppm(raw)
    assert got.shape == img.shape
    assert float(np.mean(np.abs(got - img))) < 0.01


def test_vlvd_roundtrip():
    frames = authentic_video(n=6, h=32, w=32, seed=2)
    raw = encode_vlvd(frames, fps=24.0)
    assert sniff_media(raw, "clip.vlvd") == "video"
    got, fps = decode_vlvd(raw)
    assert got.shape == frames.shape
    assert abs(fps - 24.0) < 1e-3
    assert float(np.mean(np.abs(got - frames))) < 0.02


def test_decode_image_bytes_png_and_ppm():
    img = authentic_image(24, 24, seed=6)
    assert decode_image_bytes(encode_png(img), "a.png").shape == (24, 24, 3)
    assert decode_image_bytes(encode_ppm(img), "a.ppm").shape == (24, 24, 3)
