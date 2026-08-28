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
