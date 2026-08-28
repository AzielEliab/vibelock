"""WAV round-trip. Analyze does not write audio back to disk."""

from __future__ import annotations

import numpy as np

from vibelock.io import load_audio, write_wav


def test_wav_roundtrip(tmp_path, authentic_pair):
    path = tmp_path / "a.wav"
    write_wav(path, authentic_pair.audio, authentic_pair.sr)
    data, sr = load_audio(path)
    assert sr == authentic_pair.sr
    assert data.ndim == 1
    assert data.size == authentic_pair.audio.size
    # 16-bit PCM: correlation, not bit identity.
    corr = np.corrcoef(authentic_pair.audio, data)[0, 1]
    assert corr > 0.99


def test_resample_on_load(tmp_path, authentic_pair):
    path = tmp_path / "b.wav"
    write_wav(path, authentic_pair.audio, authentic_pair.sr)
    data, sr = load_audio(path, target_sr=8000)
    assert sr == 8000
    expected = int(round(authentic_pair.audio.size * 8000 / authentic_pair.sr))
    assert abs(data.size - expected) <= 8


def test_missing_file_raises():
    import pytest

    with pytest.raises(FileNotFoundError):
        load_audio("/no/such/vibelock/file.wav")
