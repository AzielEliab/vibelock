"""CLI: analyze prints score + reason codes and exits 0; version works."""

from __future__ import annotations

import json

from vibelock.cli import main
from vibelock.io import write_wav


def test_version(capsys):
    rc = main(["version"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "vibelock" in out.lower()
    assert "0.1.0" in out


def test_analyze_audio_only_json(tmp_path, authentic_pair, capsys):
    wav = tmp_path / "air.wav"
    write_wav(wav, authentic_pair.audio, authentic_pair.sr)
    rc = main(["analyze", str(wav), "--json"])
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    assert "score" in payload
    assert payload["mode"] == "audio_only"
    assert isinstance(payload["reason_codes"], list)
    assert 0.0 <= payload["score"] <= 1.0


def test_analyze_dual_channel_human(tmp_path, authentic_pair, capsys):
    air = tmp_path / "air.wav"
    vib = tmp_path / "vib.wav"
    write_wav(air, authentic_pair.audio, authentic_pair.sr)
    write_wav(vib, authentic_pair.vibration, authentic_pair.sr)
    rc = main(["analyze", str(air), "--vibration", str(vib)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "authenticity score" in out.lower()
    assert "dual_channel" in out
    assert "Reason codes:" in out


def test_analyze_missing_file_nonzero(capsys):
    rc = main(["analyze", "/no/such/vibelock.wav"])
    err = capsys.readouterr().err
    assert rc != 0
    assert "error" in err.lower()
