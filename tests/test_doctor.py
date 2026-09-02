"""vibelock doctor and doctor --verify. No network."""

from __future__ import annotations

import json
import os

from vibelock.cli import _build_parser, main
from vibelock.doctor import TELEMETRY, run


def test_help_lists_doctor() -> None:
    text = _build_parser().format_help()
    assert "doctor" in text
    analyze = _build_parser().parse_args(["analyze", "x.wav", "--verify"])
    assert analyze.verify is True
    doc = _build_parser().parse_args(["doctor", "--verify"])
    assert doc.verify is True


def test_doctor_healthy(capsys) -> None:
    rc = main(["doctor"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "healthy" in out.lower()
    assert "telemetry" in out.lower()
    assert "advisory" in out.lower() or "courtroom" in out.lower()


def test_doctor_verify_json(capsys) -> None:
    rc = main(["doctor", "--verify", "--json"])
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    assert payload["ok"] is True
    assert payload["version"] == "0.2.0"
    assert payload["telemetry"] is False
    assert payload["courtroom_proof"] is False
    names = {c["name"] for c in payload["checks"]}
    assert "verify" in names
    assert "wav_roundtrip" in names
    assert "reject_non_audio" in names
    assert "truncated" in names
    assert all(c["ok"] for c in payload["checks"])


def test_run_has_no_telemetry() -> None:
    assert TELEMETRY is False
    payload = run(verify=False)
    assert payload["telemetry"] is False


def test_debug_env_logs(monkeypatch, capsys) -> None:
    monkeypatch.setenv("VIBELOCK_DEBUG", "1")
    rc = main(["doctor", "--json"])
    err = capsys.readouterr().err
    assert rc == 0
    assert "vibelock debug:" in err
