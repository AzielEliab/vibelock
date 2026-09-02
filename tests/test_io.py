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


def test_rejects_non_audio(tmp_path):
    import pytest

    from vibelock.io import AudioError

    path = tmp_path / "note.txt"
    path.write_text("hello this is not audio", encoding="utf-8")
    with pytest.raises(AudioError, match="not audio"):
        load_audio(path)


def test_truncated_wav_does_not_crash(tmp_path):
    import pytest

    from vibelock.io import AudioError, decode_audio_bytes

    path = tmp_path / "cut.wav"
    path.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")
    with pytest.raises(AudioError):
        load_audio(path)
    with pytest.raises(AudioError):
        decode_audio_bytes(b"RIFF", name="tiny.wav")


def test_max_size_rejected(tmp_path):
    import pytest

    from vibelock.io import AudioError, load_audio_ex

    path = tmp_path / "big.wav"
    path.write_bytes(b"RIFF" + b"\x00" * 80)
    with pytest.raises(AudioError, match="too big"):
        load_audio_ex(path, max_bytes=16)


def test_png_named_wav_rejected(tmp_path):
    import pytest

    from vibelock.io import AudioError

    path = tmp_path / "trick.wav"
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20)
    with pytest.raises(AudioError, match="not audio"):
        load_audio(path)


def test_load_audio_ex_hash(tmp_path, authentic_pair):
    from vibelock.io import load_audio_ex, sha256_file

    path = tmp_path / "c.wav"
    write_wav(path, authentic_pair.audio, authentic_pair.sr)
    _data, sr, meta = load_audio_ex(path)
    assert sr == authentic_pair.sr
    assert meta["sha256"] == sha256_file(path)
    assert len(meta["sha256"]) == 64
