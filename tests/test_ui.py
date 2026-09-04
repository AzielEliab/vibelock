"""Smoke the localhost UI. No network beyond 127.0.0.1."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

from vibelock.cli import _build_parser
from vibelock.ui import DEFAULT_HOST, DEFAULT_PORT, Handler
from http.server import ThreadingHTTPServer


def test_cli_ui_defaults() -> None:
    args = _build_parser().parse_args(["ui"])
    assert args.host == "127.0.0.1"
    assert args.host == DEFAULT_HOST
    assert args.port == 8760
    assert args.port == DEFAULT_PORT
    serve = _build_parser().parse_args(["serve"])
    assert serve.cmd in ("ui", "serve")
    assert serve.host == "127.0.0.1"


def _start():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, thread


def test_ui_get_root_contains_product_name() -> None:
    httpd, thread = _start()
    try:
        port = httpd.server_address[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as res:
            body = res.read()
            assert res.status == 200
            assert b"VibeLock" in body
            assert b"127.0.0.1" in body
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def test_ui_synth_returns_score() -> None:
    httpd, thread = _start()
    try:
        port = httpd.server_address[1]
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/synth",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as res:
            payload = json.loads(res.read().decode("utf-8"))
            assert res.status == 200
            assert 0.0 <= payload["score"] <= 1.0
            assert payload["mode"] == "dual_channel"
            assert payload["synthetic"] is True
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def test_ui_root_has_add_file_and_views() -> None:
    httpd, thread = _start()
    try:
        port = httpd.server_address[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as res:
            body = res.read()
            assert b"Add file" in body
            assert b"Export JSON report" in body
            assert b"Simple" in body
            assert b"Advanced" in body
            assert b"Sample tone" in body
            assert b"Sample photo" in body
            assert b"Sample deepfake" in body
            assert b"courtroom" in body
            assert b"consistent" in body
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def test_ui_capabilities() -> None:
    httpd, thread = _start()
    try:
        port = httpd.server_address[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/capabilities", timeout=5) as res:
            payload = json.loads(res.read().decode("utf-8"))
            assert payload["ok"] is True
            assert payload["telemetry"] is False
            assert payload["loopback"] is True
            assert "wav" in payload["formats"]
            assert payload["courtroom_proof"] is False
            assert "courtroom" in payload["limitation"]
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def test_ui_photo_and_deepfake() -> None:
    httpd, thread = _start()
    try:
        port = httpd.server_address[1]
        for path, flag in (("/api/photo", "sample_photo"), ("/api/deepfake", "sample_deepfake")):
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}{path}",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=45) as res:
                payload = json.loads(res.read().decode("utf-8"))
                assert res.status == 200
                assert 0.0 <= payload["score"] <= 1.0
                assert payload[flag] is True
                assert "courtroom" in payload["limitation"]
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def test_ui_tone_returns_report() -> None:
    httpd, thread = _start()
    try:
        port = httpd.server_address[1]
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/tone",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as res:
            payload = json.loads(res.read().decode("utf-8"))
            assert res.status == 200
            assert 0.0 <= payload["score"] <= 1.0
            assert payload["plain"] in {"consistent", "inconsistent"}
            assert payload["sample_tone"] is True
            assert "courtroom" in payload["limitation"]
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def test_ui_analyze_wav_and_hashes(tmp_path, authentic_pair) -> None:
    import base64

    from vibelock.io import write_wav

    wav = tmp_path / "air.wav"
    write_wav(wav, authentic_pair.audio, authentic_pair.sr)
    blob = base64.b64encode(wav.read_bytes()).decode("ascii")
    httpd, thread = _start()
    try:
        port = httpd.server_address[1]
        body = json.dumps({"audio_b64": blob, "filename": "air.wav"}).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/analyze",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as res:
            payload = json.loads(res.read().decode("utf-8"))
            assert res.status == 200
            assert payload["hashes"]["sha256"]
            assert payload["plain"] in {"consistent", "inconsistent"}
            assert payload["courtroom_proof"] is False
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def test_ui_rejects_non_audio() -> None:
    import base64

    blob = base64.b64encode(b"hello this is not audio").decode("ascii")
    httpd, thread = _start()
    try:
        port = httpd.server_address[1]
        body = json.dumps({"audio_b64": blob, "filename": "note.txt"}).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/analyze",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            raise AssertionError("expected HTTP 400")
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
            payload = json.loads(exc.read().decode("utf-8"))
            assert "not audio" in payload["error"].lower() or "wav" in payload["error"].lower()
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def test_ui_truncated_wav() -> None:
    import base64

    blob = base64.b64encode(b"RIFF\x00\x00\x00\x00WAVEfmt ").decode("ascii")
    httpd, thread = _start()
    try:
        port = httpd.server_address[1]
        body = json.dumps({"audio_b64": blob, "filename": "cut.wav"}).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/analyze",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            raise AssertionError("expected HTTP 400")
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
            payload = json.loads(exc.read().decode("utf-8"))
            err = payload["error"].lower()
            assert "broken" in err or "cut" in err or "not audio" in err
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)
