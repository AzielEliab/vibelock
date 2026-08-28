"""vibelock listen: mock the mic. Never opens a real device."""

from __future__ import annotations

import json

import numpy as np
import pytest

from vibelock.cli import _build_parser, main
from vibelock.tether import TetherError, listen_cli, run_listen, score_window
from vibelock.ui import LOOPBACK, make_server


def test_help_lists_ui_and_version() -> None:
    text = _build_parser().format_help()
    assert "ui" in text
    assert "version" in text
    assert "listen" in text
    assert "127.0.0.1:8760" in text or "vibelock ui" in text


def test_listen_mocked_mic_pass(monkeypatch, authentic_pair, capsys) -> None:
    chunk = authentic_pair.audio[: int(0.4 * authentic_pair.sr)]

    def fake_chunks(*, seconds, window_s, sr):
        yield chunk

    monkeypatch.setattr("vibelock.tether.mic_chunks", fake_chunks)
    rc = main(["listen", "--seconds", "0.4", "--window", "0.4", "--threshold", "0.0"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "PASS" in out
    assert "window 1" in out


def test_listen_gate_exits_nonzero_on_risk(monkeypatch, capsys) -> None:
    silence = np.zeros(8000, dtype=np.float64)

    def fake_chunks(*, seconds, window_s, sr):
        yield silence

    rc = listen_cli(
        seconds=0.5,
        window_s=0.5,
        sr=16000,
        threshold=0.99,
        gate=True,
        chunks_factory=fake_chunks,
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert "RISK" in captured.out or "RISK" in captured.err
    assert "gate" in captured.err.lower()


def test_listen_json_window(monkeypatch, authentic_pair, capsys) -> None:
    chunk = authentic_pair.audio[: int(0.4 * authentic_pair.sr)]

    def fake_chunks(*, seconds, window_s, sr):
        yield chunk

    n, score, verdict = run_listen(
        fake_chunks(seconds=0.4, window_s=0.4, sr=authentic_pair.sr),
        sr=authentic_pair.sr,
        threshold=0.0,
        as_json=True,
    )
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert n == 1
    assert payload["verdict"] == "PASS"
    assert payload["window"] == 1
    assert 0.0 <= payload["score"] <= 1.0
    assert verdict == "PASS"
    assert score is not None


def test_score_window_verdicts() -> None:
    from vibelock.scoring import AnalysisResult

    class Fake(AnalysisResult):
        pass

    # exercise real analyze on silence → RISK at high threshold
    audio = np.zeros(4000, dtype=np.float64)
    result, verdict = score_window(audio, 8000, threshold=0.99)
    assert verdict in {"PASS", "RISK"}
    if result.score < 0.99:
        assert verdict == "RISK"


def test_listen_missing_sounddevice(monkeypatch, capsys) -> None:
    def boom(*, seconds, window_s, sr):
        raise TetherError("vibelock listen needs the optional extra [tether]")
        yield  # pragma: no cover

    rc = listen_cli(chunks_factory=boom, gate=False)
    err = capsys.readouterr().err
    assert rc == 2
    assert "tether" in err.lower()


def test_ui_refuses_non_loopback() -> None:
    assert "127.0.0.1" in LOOPBACK
    with pytest.raises(ValueError, match="loopback"):
        make_server(host="0.0.0.0", port=0)
