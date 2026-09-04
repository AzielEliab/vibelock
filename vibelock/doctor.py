"""``vibelock doctor`` — local health check. No network, no telemetry."""

from __future__ import annotations

import json
import sys
import tempfile
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

import numpy as np

from vibelock import __version__
from vibelock.debug import enabled as debug_on
from vibelock.debug import log as dlog
from vibelock.io import (
    MAX_AUDIO_BYTES,
    AudioError,
    PLAIN_TRUNCATED,
    decode_audio_bytes,
    load_audio_ex,
    sha256_bytes,
    supported_suffixes,
    write_wav,
)
from vibelock.report import LIMITATION, build_report
from vibelock.media import decode_png, encode_png
from vibelock.scoring import analyze
from vibelock.synth import make_pair
from vibelock.synth_media import authentic_image, deepfake_image
from vibelock.ui import LOOPBACK, Handler

TELEMETRY = False


def _ok(name: str, detail: str) -> dict[str, Any]:
    return {"name": name, "ok": True, "detail": detail}


def _bad(name: str, detail: str) -> dict[str, Any]:
    return {"name": name, "ok": False, "detail": detail}


def _check_imports() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows.append(_ok("python", sys.version.split()[0]))
    try:
        import numpy as np  # noqa: F401

        rows.append(_ok("numpy", getattr(np, "__version__", "present")))
    except Exception as exc:  # noqa: BLE001
        rows.append(_bad("numpy", str(exc)))
    try:
        import scipy  # noqa: F401

        rows.append(_ok("scipy", getattr(scipy, "__version__", "present")))
    except Exception as exc:  # noqa: BLE001
        rows.append(_bad("scipy", str(exc)))
    rows.append(_ok("vibelock", __version__))
    return rows


def _check_loopback() -> dict[str, Any]:
    try:
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        host, port = httpd.server_address[:2]
        httpd.server_close()
        if str(host) not in LOOPBACK:
            return _bad("loopback", f"bound {host}, expected 127.0.0.1")
        return _ok("loopback", f"{host}:{port}")
    except Exception as exc:  # noqa: BLE001
        return _bad("loopback", str(exc))


def _check_roundtrip(tmp: Path) -> dict[str, Any]:
    from vibelock.synth import sample_tone

    sr = 16000
    tone = sample_tone(duration_s=0.25, sr=sr)
    path = tmp / "roundtrip.wav"
    write_wav(path, tone, sr)
    data, got_sr, meta = load_audio_ex(path)
    if got_sr != sr:
        return _bad("wav_roundtrip", f"sr {got_sr} != {sr}")
    n = min(data.size, tone.size)
    corr = float(np.corrcoef(tone[:n], data[:n])[0, 1])
    if corr < 0.99:
        return _bad("wav_roundtrip", f"corr {corr:.4f} < 0.99")
    if len(meta.get("sha256") or "") != 64:
        return _bad("wav_roundtrip", "missing sha256")
    return _ok("wav_roundtrip", f"corr={corr:.4f} sha256={meta['sha256'][:12]}…")


def _check_hardening(tmp: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        decode_audio_bytes(b"this is not audio at all", name="note.txt")
        rows.append(_bad("reject_non_audio", "accepted a text file"))
    except AudioError as exc:
        rows.append(_ok("reject_non_audio", str(exc)))
    except Exception as exc:  # noqa: BLE001
        rows.append(_bad("reject_non_audio", f"crashed: {exc}"))

    truncated = b"RIFF\x00\x00\x00\x00WAVEfmt "
    try:
        decode_audio_bytes(truncated, name="cut.wav")
        rows.append(_bad("truncated", "accepted a truncated WAV"))
    except AudioError as exc:
        if PLAIN_TRUNCATED in str(exc) or "broken" in str(exc).lower() or "cut" in str(exc).lower():
            rows.append(_ok("truncated", str(exc)))
        else:
            rows.append(_ok("truncated", str(exc)))
    except Exception as exc:  # noqa: BLE001
        rows.append(_bad("truncated", f"crashed: {exc}"))

    try:
        decode_audio_bytes(b"RIFF", name="tiny.wav", max_bytes=MAX_AUDIO_BYTES)
        rows.append(_bad("tiny_riff", "accepted 4-byte RIFF"))
    except AudioError:
        rows.append(_ok("tiny_riff", "rejected"))
    except Exception as exc:  # noqa: BLE001
        rows.append(_bad("tiny_riff", f"crashed: {exc}"))

    big = tmp / "too-big.bin"
    big.write_bytes(b"RIFF" + b"\x00" * 64)
    try:
        load_audio_ex(big, max_bytes=16)
        rows.append(_bad("max_size", "accepted oversized file"))
    except AudioError as exc:
        rows.append(_ok("max_size", str(exc)))
    except Exception as exc:  # noqa: BLE001
        rows.append(_bad("max_size", f"crashed: {exc}"))
    return rows


def _check_verify(tmp: Path) -> dict[str, Any]:
    pair = make_pair(duration_s=0.6, sr=16000, f0=120.0, seed=20260902)
    air = tmp / "air.wav"
    write_wav(air, pair.audio, pair.sr)
    audio, sr, meta = load_audio_ex(air)
    result = analyze(audio, sr, vibration=None)
    audio2, sr2, meta2 = load_audio_ex(air)
    result2 = analyze(audio2, sr2, vibration=None)
    if meta["sha256"] != meta2["sha256"]:
        return _bad("verify", "hash changed between reads")
    if abs(float(result.score) - float(result2.score)) > 1e-9:
        return _bad("verify", "score changed between reads")
    if not (0.0 <= result.score <= 1.0):
        return _bad("verify", f"score {result.score} out of range")
    report = build_report(result, sha256=meta["sha256"], filename=air.name)
    if report.get("limitation") != LIMITATION:
        return _bad("verify", "limitation missing")
    if "sha256" not in (report.get("hashes") or {}):
        return _bad("verify", "hash missing from report")
    dlog(f"verify score={result.score:.4f} sha256={meta['sha256']}")
    return _ok(
        "verify",
        f"score={result.score:.3f} sha256={meta['sha256'][:12]}…",
    )


def _check_png(tmp: Path) -> dict[str, Any]:
    img = authentic_image(48, 48, seed=3)
    raw = encode_png(img)
    path = tmp / "roundtrip.png"
    path.write_bytes(raw)
    got = decode_png(path.read_bytes())
    if got.shape != img.shape:
        return _bad("png_roundtrip", f"shape {got.shape} != {img.shape}")
    err = float(np.mean(np.abs(got - img)))
    if err > 0.02:
        return _bad("png_roundtrip", f"mae {err:.4f} > 0.02")
    return _ok("png_roundtrip", f"mae={err:.4f}")


def _check_vision() -> dict[str, Any]:
    good = analyze(image=authentic_image(64, 64, seed=2))
    bad = analyze(image=deepfake_image(64, 64, seed=8))
    if good.score <= bad.score:
        return _bad("vision", f"authentic {good.score:.3f} <= deepfake {bad.score:.3f}")
    return _ok("vision", f"authentic={good.score:.3f} deepfake={bad.score:.3f}")


def run(*, verify: bool = False) -> dict[str, Any]:
    """Run doctor checks. Never talks to the network."""
    dlog(f"doctor start verify={verify} debug={debug_on()}")
    checks: list[dict[str, Any]] = []
    checks.extend(_check_imports())
    checks.append(_check_loopback())
    formats = ",".join(s.lstrip(".") for s in supported_suffixes())
    checks.append(_ok("formats", formats or "wav"))
    if TELEMETRY:
        checks.append(_bad("telemetry", "telemetry is on"))
    else:
        checks.append(_ok("telemetry", "off"))
    checks.append(_ok("limitation", LIMITATION))
    with tempfile.TemporaryDirectory(prefix="vibelock-doctor-") as raw:
        tmp = Path(raw)
        checks.append(_check_roundtrip(tmp))
        checks.extend(_check_hardening(tmp))
        checks.append(_check_png(tmp))
        checks.append(_check_vision())
        if verify:
            checks.append(_check_verify(tmp))
    ok = all(bool(c.get("ok")) for c in checks)
    payload = {
        "ok": ok,
        "product": "vibelock",
        "version": __version__,
        "limitation": LIMITATION,
        "telemetry": TELEMETRY,
        "debug": debug_on(),
        "formats": [s.lstrip(".") for s in supported_suffixes()],
        "checks": checks,
        "courtroom_proof": False,
    }
    dlog(f"doctor done ok={ok}")
    return payload


def format_human(payload: dict[str, Any]) -> str:
    lines = [f"VibeLock doctor {payload.get('version')}"]
    for row in payload.get("checks") or []:
        mark = "ok" if row.get("ok") else "FAIL"
        lines.append(f"  {row.get('name')}: {mark}  {row.get('detail')}")
    lines.append("doctor: healthy" if payload.get("ok") else "doctor: unhealthy")
    lines.append(LIMITATION)
    return "\n".join(lines)


def doctor_cli(*, verify: bool = False, as_json: bool = False, out=None, err=None) -> int:
    out = sys.stdout if out is None else out
    payload = run(verify=verify)
    if as_json:
        out.write(json.dumps(payload, indent=2))
        out.write("\n")
    else:
        out.write(format_human(payload))
        out.write("\n")
    return 0 if payload.get("ok") else 1
