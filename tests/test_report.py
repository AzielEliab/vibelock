"""JSON report: hashes, scores, limitation. Round-trip on disk."""

from __future__ import annotations

import json

from vibelock.io import load_audio_ex, sha256_file, write_wav
from vibelock.report import (
    LIMITATION,
    build_report,
    dumps_report,
    kid_plain,
    kid_sentence,
)
from vibelock.scoring import analyze


def test_kid_plain_words() -> None:
    assert kid_plain(0.9) == "consistent"
    assert kid_plain(0.1) == "inconsistent"
    assert "consistent" in kid_sentence(0.9)
    assert "inconsistent" in kid_sentence(0.1)


def test_report_roundtrip(tmp_path, authentic_pair) -> None:
    wav = tmp_path / "air.wav"
    write_wav(wav, authentic_pair.audio, authentic_pair.sr)
    audio, sr, meta = load_audio_ex(wav)
    result = analyze(audio, sr)
    report = build_report(result, sha256=meta["sha256"], filename=wav.name)
    assert report["limitation"] == LIMITATION
    assert report["courtroom_proof"] is False
    assert report["hashes"]["sha256"] == sha256_file(wav)
    assert report["plain"] in {"consistent", "inconsistent"}
    assert 0.0 <= report["score"] <= 1.0
    out = tmp_path / "report.json"
    out.write_text(dumps_report(report), encoding="utf-8")
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["hashes"]["sha256"] == report["hashes"]["sha256"]
    assert loaded["score"] == report["score"]
    assert "courtroom" in loaded["limitation"]
    assert "waveform" not in loaded
    assert "audio" not in loaded or loaded.get("audio") in (None, loaded.get("filename"))
