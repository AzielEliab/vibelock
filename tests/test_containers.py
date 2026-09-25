"""Container decode: PCM MP4 always, compressed formats only with ffmpeg."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from vibelock.containers import decode_pcm_mp4, encode_pcm_mp4, ffmpeg_available, open_media_bytes
from vibelock.media import MediaError
from vibelock.scoring import analyze
from vibelock.synth import make_pair


def test_pcm_mp4_roundtrip_and_channels(tmp_path: Path) -> None:
    pair = make_pair(duration_s=0.8, sr=16000, f0=120.0, seed=7)
    raw = encode_pcm_mp4(pair.audio, pair.sr)
    decoded = decode_pcm_mp4(raw)
    assert decoded is not None
    audio, sr = decoded
    assert sr == pair.sr
    assert audio.shape == pair.audio.shape
    assert float(np.max(np.abs(audio - pair.audio))) < 2.0 / 32768.0
    path = tmp_path / "voice.mp4"
    path.write_bytes(raw)
    opened = open_media_bytes(path.read_bytes(), name=path.name)
    assert opened["decoder"] == "pcm_mp4"
    assert opened["format"] in {"mp4", "m4a", "mov"}
    result = analyze(opened["audio"], opened["sr"])
    names = [c.name for c in result.channels]
    assert names == ["physics", "linguistics", "vibration", "related"]
    vib = next(c for c in result.channels if c.name == "vibration")
    assert vib.status == "insufficient"
    physics = next(c for c in result.channels if c.name == "physics")
    assert physics.status == "fired"
    assert physics.evidence == "heuristic"
    blob = result.to_dict()
    assert "waveform" not in blob
    assert "accuracy" not in blob


def test_unknown_bytes_fail_closed() -> None:
    with pytest.raises(MediaError):
        open_media_bytes(b"this is not media", name="note.txt")


def test_compressed_without_decoder_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("vibelock.containers.ffmpeg_available", lambda: False)
    monkeypatch.setattr("vibelock.containers.ffmpeg_path", lambda: None)
    # ID3 header so this is sniffed as MP3, not decoded.
    raw = b"ID3" + b"\x00" * 32
    with pytest.raises(MediaError) as exc:
        open_media_bytes(raw, name="clip.mp3")
    text = str(exc.value).lower()
    assert "ffmpeg" in text
    assert "not guess" in text or "will not guess" in text


@pytest.mark.skipif(not ffmpeg_available(), reason="ffmpeg is not on PATH")
def test_ffmpeg_mp3_and_mp4(tmp_path: Path) -> None:
    wav = tmp_path / "tone.wav"
    pair = make_pair(duration_s=0.6, sr=16000, f0=130.0, seed=3)
    from vibelock.io import write_wav

    write_wav(wav, pair.audio, pair.sr)
    mp3 = tmp_path / "tone.mp3"
    mp4 = tmp_path / "tone.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(wav), "-c:a", "libmp3lame", str(mp3)],
        check=True,
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc=size=64x64:rate=8:duration=0.6",
            "-i", str(wav),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
            str(mp4),
        ],
        check=True,
    )
    assert mp3.stat().st_size > 100
    assert mp4.stat().st_size > 100
    opened_mp3 = open_media_bytes(mp3.read_bytes(), name=mp3.name)
    assert opened_mp3["decoder"] == "ffmpeg"
    assert opened_mp3["audio"] is not None
    assert opened_mp3["audio"].size > 1000
    opened_mp4 = open_media_bytes(mp4.read_bytes(), name=mp4.name)
    assert opened_mp4["decoder"] == "ffmpeg"
    assert opened_mp4["audio"] is not None
    assert opened_mp4["frames"] is not None
    assert opened_mp4["frames"].shape[0] >= 2
    result = analyze(opened_mp4["audio"], opened_mp4["sr"], frames=opened_mp4["frames"], fps=opened_mp4["fps"])
    related = next(c for c in result.channels if c.name == "related")
    assert related.status == "fired"
    assert related.evidence == "heuristic"
    assert shutil.which("ffmpeg")
