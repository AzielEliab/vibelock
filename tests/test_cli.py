"""CLI: write a temp WAV, run vibelock.cli.main, exit 0 with a score."""

from __future__ import annotations

import json
import wave

import numpy as np
from scipy.io import wavfile

from vibelock.cli import main


def _write_wav_scipy(path, audio, sr: int) -> None:
    pcm = np.clip(np.asarray(audio, dtype=np.float64), -1.0, 1.0)
    wavfile.write(str(path), int(sr), (pcm * 32767.0).astype(np.int16))


def _write_wav_wave(path, audio, sr: int) -> None:
    pcm = np.clip(np.asarray(audio, dtype=np.float64), -1.0, 1.0)
    samples = (pcm * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(int(sr))
        wf.writeframes(samples.tobytes())


def test_version(capsys):
    rc = main(["version"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "vibelock" in out.lower()
    assert "0.1.0" in out


def test_analyze_temp_wav_scipy_exit_zero_prints_score(tmp_path, authentic_pair, capsys):
    wav = tmp_path / "air.wav"
    _write_wav_scipy(wav, authentic_pair.audio, authentic_pair.sr)
    rc = main(["analyze", str(wav)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "score" in out.lower()
    # Human formatter prints a numeric score.
    assert any(ch.isdigit() for ch in out)


def test_analyze_temp_wav_wave_module_json(tmp_path, authentic_pair, capsys):
    wav = tmp_path / "air.wav"
    _write_wav_wave(wav, authentic_pair.audio, authentic_pair.sr)
    rc = main(["analyze", str(wav), "--json"])
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    assert "score" in payload
    assert 0.0 <= payload["score"] <= 1.0
    assert payload["mode"] == "audio_only"


def test_analyze_dual_channel(tmp_path, authentic_pair, capsys):
    air = tmp_path / "air.wav"
    vib = tmp_path / "vib.wav"
    _write_wav_scipy(air, authentic_pair.audio, authentic_pair.sr)
    _write_wav_scipy(vib, authentic_pair.vibration, authentic_pair.sr)
    rc = main(["analyze", str(air), "--vibration", str(vib)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "score" in out.lower()
    assert "dual_channel" in out
