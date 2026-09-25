"""Hosted file-deepfake contract: channels, no container decode, no accuracy claim."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "workers" / "download-tracker"


def test_homepage_accepts_av_and_cites_channels() -> None:
    home = (WORKER / "src" / "homepage.js").read_text(encoding="utf-8")
    assert 'id="channels"' in home
    assert ".mp4" in home
    assert ".mp3" in home
    assert "risk index" in home
    assert "does not decode" in home.lower() or "does not decode the container" in home
    runtime = (WORKER / "src" / "runtime.js").read_text(encoding="utf-8")
    assert "container_b64" in runtime
    assert "decodes_containers" in runtime
    assert "LINGUISTIC_RHYTHM_METRONOME" in runtime
    assert "accuracy_claim" in runtime
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "linguistics" in skill
    assert "does not decode container bytes" in skill or "does **not** decode container bytes" in skill


def test_hosted_detect_channels_script() -> None:
    script = WORKER / "scripts" / "verify-file-channels.mjs"
    proc = subprocess.run(
        ["node", str(script)],
        cwd=str(WORKER),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "ok" in proc.stdout