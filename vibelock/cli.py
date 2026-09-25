"""Command-line interface for VibeLock.

    vibelock ui [--host 127.0.0.1] [--port 8760]
    vibelock version
    vibelock doctor [--verify] [--json]
    vibelock analyze MEDIA [--vibration FILE] [--video PATH] [--image PATH]
             [--sr HZ] [--fps N] [--json] [--verify] [--export PATH]
    vibelock detect …   (alias of analyze — A/V deepfake engine)
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
import re
import sys
from pathlib import Path
from typing import Sequence

from vibelock import __version__
from vibelock.debug import log as dlog
from vibelock.io import AudioError, load_audio_ex
from vibelock.report import build_report, dumps_report, format_report
from vibelock.scoring import analyze

_NEXT_HELP = "Try: vibelock ui   or   vibelock --help"
_NEXT_FILE = "Try: vibelock analyze recording.wav   or   vibelock ui"
_CHOICE = re.compile(r"invalid choice: '([^']*)'")

WELCOME = """\
VibeLock checks whether a recording, a photo, or a short clip looks physically consistent with a real voice or camera.

Open the app:
  vibelock ui

Or check a file:
  vibelock analyze recording.wav

Also: vibelock doctor
Help: vibelock --help

Author: Aziel Eliab
"""

HELP = """\
vibelock — check a recording, photo, or short clip

usage: vibelock <command> [options]

VibeLock checks whether media looks physically consistent with a real voice or camera.
Author: Aziel Eliab

Start
  (no command)       Welcome and the next step
  ui, serve          Open http://127.0.0.1:8760/

Common
  analyze MEDIA      Check a WAV, PNG, PPM, .vlvd file, or a frame folder
  detect MEDIA       Same as analyze
  doctor             Check that VibeLock can run on this machine
  version            Print the version

Advanced
  listen             Score the default microphone in short windows
  analyze --vibration FILE
                     Compare a body-coupled vibration recording
  analyze --video PATH
                     Compare a frame stack with the audio
  analyze --image PATH
                     Compare a still with the audio
  analyze --verify   Re-read the file and confirm the score and hash
  analyze --export PATH
                     Write a JSON report
  --json             Machine-readable output on analyze, doctor, and listen

Examples
  vibelock
  vibelock ui
  vibelock analyze recording.wav
  vibelock doctor
  vibelock analyze recording.wav --json
"""


def _plain_arg_error(message: str) -> str:
    """Turn an argparse complaint into a reason plus a next step."""
    match = _CHOICE.search(message or "")
    if match:
        return f'Unknown command "{match.group(1)}". {_NEXT_HELP}'
    text = message or "That command could not be read."
    if "required" in text and "audio" in text:
        return f"Add a media file. {_NEXT_FILE}"
    if "required" in text and "cmd" in text:
        return f"Choose a command. {_NEXT_HELP}"
    if "invalid int value" in text and "--port" in text:
        return "The port needs to be a whole number. Try: vibelock ui --port 8760"
    if text.startswith("unrecognized arguments"):
        return f"Unknown option ({text}). Try: vibelock --help"
    reason = text[0].upper() + text[1:] if text else "That command could not be read."
    if not reason.endswith("."):
        reason += "."
    return f"{reason} Try: vibelock --help"


class HumanParser(argparse.ArgumentParser):
    """Git-style help and plain errors. Subcommand options stay on the parser."""

    def format_help(self) -> str:
        if self.prog == "vibelock":
            return HELP
        return super().format_help()

    def error(self, message: str) -> None:
        sys.stderr.write(_plain_arg_error(message) + "\n")
        raise SystemExit(2)


def _err(message: object, hint: str = _NEXT_HELP) -> int:
    text = str(message).rstrip()
    if not text.lower().startswith("error:"):
        text = f"error: {text}"
    sys.stderr.write(text + "\n")
    if hint and hint not in text:
        sys.stderr.write(hint + "\n")
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = HumanParser(
        prog="vibelock",
        description="VibeLock checks a recording, photo, or short clip. Author: Aziel Eliab.",
    )
    sub = parser.add_subparsers(dest="cmd", required=False, parser_class=HumanParser)

    p_an = sub.add_parser(
        "analyze",
        aliases=["detect"],
        help="Score audio, an image, a frame stack, or an A/V pair.",
    )
    p_an.add_argument(
        "audio",
        help="Path to WAV / PNG / PPM / .vlvd / frame folder (FLAC/MP3 if supported).",
    )
    p_an.add_argument(
        "--vibration",
        "-v",
        default=None,
        help="Optional body-coupled vibration WAV (jaw accel / contact mic / IMU).",
    )
    p_an.add_argument(
        "--image",
        default=None,
        help="Optional still (PNG/PPM) analyzed with the audio.",
    )
    p_an.add_argument(
        "--video",
        default=None,
        help="Optional frame stack (.vlvd, .npy, or a folder of PNG/PPM).",
    )
    p_an.add_argument(
        "--fps",
        type=float,
        default=None,
        help="Frame rate for a video folder or stack (default 25).",
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
        _err(exc, _NEXT_FILE)
        raise SystemExit(2) from exc
    except AudioError as exc:
        _err(exc, _NEXT_FILE)
        raise SystemExit(2) from exc
    except Exception as exc:  # noqa: BLE001 — surface decode problems plainly
        _err(f"failed to read {label}: {exc}", _NEXT_FILE)
        raise SystemExit(2) from exc


def _load_primary(path: str, target_sr: int | None, fps: float | None):
    """Load WAV / image / video / frame folder. Raises FileNotFoundError or MediaError."""
    from vibelock.media import MediaError, load_image, load_video, sniff_media

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Media file not found: {p}")
    if p.is_dir():
        frames, rate, meta = load_video(p, fps=fps)
        return {"kind": "video", "frames": frames, "fps": rate, "meta": meta, "audio": None, "sr": 0, "image": None}
    raw = p.read_bytes()
    kind = sniff_media(raw, p.name)
    if kind == "image":
        img, meta = load_image(p)
        return {"kind": "image", "image": img, "meta": meta, "audio": None, "sr": 0, "frames": None, "fps": 0.0}
    if kind in {"video", "ndarray"}:
        frames, rate, meta = load_video(p, fps=fps)
        return {"kind": "video", "frames": frames, "fps": rate, "meta": meta, "audio": None, "sr": 0, "image": None}
    # Audio (or a rejected non-media file via AudioError).
    audio, sr, meta = load_audio_ex(path, target_sr=target_sr)
    return {"kind": "audio", "audio": audio, "sr": sr, "meta": meta, "image": None, "frames": None, "fps": 0.0}


def _analyze_cmd(args: argparse.Namespace) -> int:
    from vibelock.media import MediaError, load_image, load_video

    dlog(f"analyze {args.audio} verify={args.verify}")
    try:
        primary = _load_primary(args.audio, args.sr, getattr(args, "fps", None))
    except FileNotFoundError as exc:
        return _err(exc, _NEXT_FILE)
    except (AudioError, MediaError) as exc:
        return _err(exc, _NEXT_FILE)
    except Exception as exc:  # noqa: BLE001
        return _err(f"failed to read media: {exc}", _NEXT_FILE)

    audio = primary.get("audio")
    sr = int(primary.get("sr") or 0)
    image = primary.get("image")
    frames = primary.get("frames")
    fps = float(primary.get("fps") or 0.0)
    meta = primary.get("meta") or {}

    vibration = None
    vib_hash = None
    if args.vibration:
        try:
            vibration, _vsr, vmeta = load_audio_ex(args.vibration, target_sr=sr or args.sr)
        except FileNotFoundError as exc:
            return _err(exc, _NEXT_FILE)
        except AudioError as exc:
            return _err(exc, _NEXT_FILE)
        except Exception as exc:  # noqa: BLE001
            return _err(f"failed to read vibration: {exc}", _NEXT_FILE)
        vib_hash = vmeta.get("sha256")

    extra_image_hash = None
    extra_video_hash = None
    if getattr(args, "image", None) and image is None:
        try:
            image, imeta = load_image(args.image)
            extra_image_hash = imeta.get("sha256")
        except (FileNotFoundError, MediaError) as exc:
            return _err(exc, _NEXT_FILE)
    if getattr(args, "video", None) and frames is None:
        try:
            frames, fps, vmeta = load_video(args.video, fps=getattr(args, "fps", None))
            extra_video_hash = vmeta.get("sha256")
        except (FileNotFoundError, MediaError) as exc:
            return _err(exc, _NEXT_FILE)

    if audio is None and image is None and frames is None:
        return _err("nothing to analyze", _NEXT_FILE)

    result = analyze(
        audio,
        sr or None,
        vibration=vibration,
        image=image,
        frames=frames,
        fps=fps or None,
    )
    extra: dict = {}
    if extra_image_hash:
        extra["sha256_image"] = extra_image_hash
    if extra_video_hash:
        extra["sha256_video"] = extra_video_hash
    if args.verify:
        try:
            again = _load_primary(args.audio, args.sr, getattr(args, "fps", None))
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"error: verify failed to re-read media: {exc}\n")
            sys.stderr.write("Try the file again, or run: vibelock doctor --verify\n")
            return 1
        meta2 = again.get("meta") or {}
        result2 = analyze(
            again.get("audio"),
            again.get("sr") or None,
            vibration=vibration,
            image=again.get("image") if again.get("image") is not None else image,
            frames=again.get("frames") if again.get("frames") is not None else frames,
            fps=(again.get("fps") or fps) or None,
        )
        if meta2.get("sha256") != meta.get("sha256"):
            sys.stderr.write("error: verify failed: file hash changed between reads\n")
            sys.stderr.write("Try the file again, or run: vibelock doctor --verify\n")
            return 1
        if abs(float(result2.score) - float(result.score)) > 1e-9:
            sys.stderr.write("error: verify failed: score did not match\n")
            sys.stderr.write("Try the file again, or run: vibelock doctor --verify\n")
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
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        if code is None or code == 0:
            return 0
        return int(code) if isinstance(code, int) else 2

    if args.cmd is None:
        sys.stdout.write(WELCOME)
        return 0

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
            return _err(exc, "Try: vibelock ui")
        except OSError as exc:
            return _err(
                f"could not open {args.host}:{args.port} ({exc.strerror or exc})",
                f"Try: vibelock ui --port {int(args.port) + 1}",
            )
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

    if args.cmd in ("analyze", "detect"):
        return _analyze_cmd(args)

    parser.error(f"unknown command {args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
