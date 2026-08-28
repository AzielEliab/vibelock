"""Command-line interface for VibeLock.

    vibelock ui [--host 127.0.0.1] [--port 8760]
    vibelock version
    vibelock analyze AUDIO [--vibration FILE] [--sr HZ] [--json]
    vibelock listen [--seconds N] [--window S] [--threshold T] [--gate]

Analyze always exits 0 on a completed run (including low scores). A
nonzero exit is reserved for usage / I/O errors so scripts can tell
"this recording looks synthetic" from "the tool failed."

``listen`` scores YOUR default microphone in short windows (optional
extra ``[tether]``). ``--gate`` exits nonzero if the last window is RISK.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from vibelock import __version__
from vibelock.io import load_audio
from vibelock.scoring import analyze, format_human


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vibelock",
        description=(
            "VibeLock — evaluate whether audio is physically consistent "
            "with human vocal vibration (Aziel Eliab, July 2026). "
            "Local UI: `vibelock ui` at http://127.0.0.1:8760."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_an = sub.add_parser("analyze", help="Score a recording (dual-channel or audio-only).")
    p_an.add_argument("audio", help="Path to air-microphone WAV.")
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
        help="Machine-readable JSON (score, reason codes, per-check metrics).",
    )

    sub.add_parser("version", help="Print the VibeLock version and exit.")

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


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "version":
        sys.stdout.write(f"vibelock {__version__}\n")
        return 0

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
        try:
            audio, sr = load_audio(args.audio, target_sr=args.sr)
        except FileNotFoundError as exc:
            sys.stderr.write(f"error: {exc}\n")
            return 2
        except Exception as exc:  # noqa: BLE001 — surface wav decode problems
            sys.stderr.write(f"error: failed to read audio: {exc}\n")
            return 2

        vibration = None
        if args.vibration:
            try:
                vibration, vsr = load_audio(args.vibration, target_sr=sr)
            except FileNotFoundError as exc:
                sys.stderr.write(f"error: {exc}\n")
                return 2
            except Exception as exc:  # noqa: BLE001
                sys.stderr.write(f"error: failed to read vibration: {exc}\n")
                return 2
            if vsr != sr:
                # load_audio already resampled to `sr` via target_sr.
                pass

        result = analyze(audio, sr, vibration=vibration)
        if args.json:
            sys.stdout.write(json.dumps(result.to_dict(), indent=2))
            sys.stdout.write("\n")
        else:
            sys.stdout.write(format_human(result))
            sys.stdout.write("\n")
        return 0

    parser.error(f"unknown command {args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
