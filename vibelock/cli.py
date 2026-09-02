"""Command-line interface for VibeLock.

    vibelock ui [--host 127.0.0.1] [--port 8760]
    vibelock version
    vibelock doctor [--verify] [--json]
    vibelock analyze AUDIO [--vibration FILE] [--sr HZ] [--json] [--verify] [--export PATH]
    vibelock listen [--seconds N] [--window S] [--threshold T] [--gate]

Analyze always exits 0 on a completed run (including low scores). A
nonzero exit is reserved for usage / I/O errors so scripts can tell
"this recording looks synthetic" from "the tool failed."

``listen`` scores YOUR default microphone in short windows (optional
extra ``[tether]``). ``--gate`` exits nonzero if the last window is RISK.

``doctor --verify`` round-trips a synthetic WAV and checks hashes/scores.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from vibelock import __version__
from vibelock.debug import log as dlog
from vibelock.io import AudioError, load_audio_ex
from vibelock.report import build_report, dumps_report, format_report
from vibelock.scoring import analyze, format_human


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vibelock",
        description=(
            "VibeLock — evaluate whether audio is physically consistent "
            "with human vocal vibration (Aziel Eliab, July 2026). "
            "Advisory, not courtroom proof. "
            "Local UI: `vibelock ui` at http://127.0.0.1:8760."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_an = sub.add_parser("analyze", help="Score a recording (dual-channel or audio-only).")
    p_an.add_argument("audio", help="Path to air-microphone WAV (FLAC/MP3 if supported).")
    p_an.add_argument(
        "--vibration",
        "-v",
        default=None,
        help="Optional body-coupled vibration WAV (jaw accel / contact mic / IMU).",
    )
    p_an.add_argument(
        "--sr",
        type=int,
        default=None,
        metavar="HZ",
        help="Resample both channels to this rate before analysis.",
    )
    p_an.add_argument(
        "--json",
        action="store_true",
        help="Machine-readable JSON (score, hashes, reason codes, limitation).",
    )
    p_an.add_argument(
        "--verify",
        action="store_true",
        help="Re-read the file and confirm the score and SHA-256 match.",
    )
    p_an.add_argument(
        "--export",
        default=None,
        metavar="PATH",
        help="Write a JSON report (hashes, scores, limitation) to PATH.",
    )

    sub.add_parser("version", help="Print the VibeLock version and exit.")

    p_doc = sub.add_parser("doctor", help="Check that VibeLock can run on this machine.")
    p_doc.add_argument(
        "--verify",
        action="store_true",
        help="Also round-trip a synthetic WAV and check the score + hash.",
    )
    p_doc.add_argument("--json", action="store_true", help="Machine-readable JSON.")

    p_ui = sub.add_parser("ui", aliases=["serve"], help="Run the localhost UI (127.0.0.1:8760).")
    p_ui.add_argument("--host", default="127.0.0.1", help="Bind host (default 127.0.0.1).")
    p_ui.add_argument("--port", type=int, default=8760, help="Bind port (default 8760).")

    p_listen = sub.add_parser(
        "listen",
        help="Score YOUR default mic in windows (needs extra [tether]). --gate exits 1 if last window is RISK.",
    )
    p_listen.add_argument("--seconds", type=float, default=3.0, help="Capture length in seconds (0 = until Ctrl-C).")
    p_listen.add_argument("--window", type=float, default=1.0, dest="window_s", help="Window length in seconds (default 1).")
    p_listen.add_argument("--sr", type=int, default=16000, help="Capture sample rate (default 16000).")
    p_listen.add_argument("--threshold", type=float, default=0.5, help="PASS if window score >= this (default 0.5).")
    p_listen.add_argument(
        "--gate",
        action="store_true",
        help="Exit nonzero if the last window is RISK (below threshold).",
    )
    p_listen.add_argument("--json", action="store_true", help="JSON per window.")
    return parser


def _load_or_fail(path: str, target_sr: int | None, label: str):
    try:
        return load_audio_ex(path, target_sr=target_sr)
    except FileNotFoundError as exc:
        sys.stderr.write(f"error: {exc}\n")
        raise SystemExit(2) from exc
    except AudioError as exc:
        sys.stderr.write(f"error: {exc}\n")
        raise SystemExit(2) from exc
    except Exception as exc:  # noqa: BLE001 — surface decode problems plainly
        sys.stderr.write(f"error: failed to read {label}: {exc}\n")
        raise SystemExit(2) from exc


def _analyze_cmd(args: argparse.Namespace) -> int:
    dlog(f"analyze {args.audio} verify={args.verify}")
    try:
        audio, sr, meta = load_audio_ex(args.audio, target_sr=args.sr)
    except FileNotFoundError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2
    except AudioError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"error: failed to read audio: {exc}\n")
        return 2

    vibration = None
    vib_hash = None
    if args.vibration:
        try:
            vibration, _vsr, vmeta = load_audio_ex(args.vibration, target_sr=sr)
        except FileNotFoundError as exc:
            sys.stderr.write(f"error: {exc}\n")
            return 2
        except AudioError as exc:
            sys.stderr.write(f"error: {exc}\n")
            return 2
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"error: failed to read vibration: {exc}\n")
            return 2
        vib_hash = vmeta.get("sha256")

    result = analyze(audio, sr, vibration=vibration)
    extra: dict = {}
    if args.verify:
        try:
            audio2, sr2, meta2 = load_audio_ex(args.audio, target_sr=args.sr)
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"error: verify failed to re-read audio: {exc}\n")
            return 1
        result2 = analyze(audio2, sr2, vibration=vibration)
        if meta2.get("sha256") != meta.get("sha256"):
            sys.stderr.write("error: verify failed: file hash changed between reads\n")
            return 1
        if abs(float(result2.score) - float(result.score)) > 1e-9:
            sys.stderr.write("error: verify failed: score did not match\n")
            return 1
        extra["verified"] = True
        dlog("verify ok")

    report = build_report(
        result,
        sha256=meta.get("sha256"),
        sha256_vibration=vib_hash,
        filename=meta.get("filename"),
        extra=extra,
    )

    if args.export:
        Path(args.export).write_text(dumps_report(report), encoding="utf-8")
        dlog(f"exported {args.export}")

    if args.json:
        sys.stdout.write(json.dumps(report, indent=2))
        sys.stdout.write("\n")
    else:
        sys.stdout.write(format_report(report))
        sys.stdout.write("\n")
        if not args.json:
            # Keep the word "score" for existing tests even if format_report changes.
            pass
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "version":
        sys.stdout.write(f"vibelock {__version__}\n")
        return 0

    if args.cmd == "doctor":
        from vibelock.doctor import doctor_cli

        return doctor_cli(verify=args.verify, as_json=args.json)

    if args.cmd in ("ui", "serve"):
        from vibelock.ui import serve

        try:
            serve(host=args.host, port=args.port)
        except ValueError as exc:
            sys.stderr.write(f"error: {exc}\n")
            return 2
        return 0

    if args.cmd == "listen":
        from vibelock.tether import listen_cli

        return listen_cli(
            seconds=args.seconds,
            window_s=args.window_s,
            sr=args.sr,
            threshold=args.threshold,
            gate=args.gate,
            as_json=args.json,
        )

    if args.cmd == "analyze":
        return _analyze_cmd(args)

    parser.error(f"unknown command {args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
