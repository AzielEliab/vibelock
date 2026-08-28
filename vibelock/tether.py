"""Optional live-mic tether for VibeLock.

``vibelock listen`` scores short windows from *your* default input
device only. It is not a room monitor, not a keylogger, and not a
network stream. Raw samples are scored in-process and discarded.

Requires the optional extra::

    pip install -e ".[tether]"

Tests mock ``mic_chunks`` so CI never opens a device.
"""

from __future__ import annotations

import json
import sys
from typing import Callable, Iterable, Iterator, Sequence

import numpy as np

from vibelock.scoring import AnalysisResult, analyze

DEFAULT_SR = 16000
DEFAULT_WINDOW_S = 1.0
DEFAULT_SECONDS = 3.0
DEFAULT_THRESHOLD = 0.5

TETHER_HINT = (
    "vibelock listen needs the optional extra [tether] (sounddevice). "
    'Install with: pip install -e ".[tether]"'
)


class TetherError(RuntimeError):
    """Mic extra missing, device failure, or usage error."""


def load_sounddevice():
    """Import sounddevice. Isolated so tests can mock the import."""
    try:
        import sounddevice as sd  # type: ignore[import-untyped]
    except ImportError as exc:
        raise TetherError(TETHER_HINT) from exc
    return sd


def score_window(
    audio: np.ndarray,
    sr: int,
    *,
    threshold: float = DEFAULT_THRESHOLD,
) -> tuple[AnalysisResult, str]:
    """Score one mono window. ``PASS`` if score >= threshold else ``RISK``."""
    result = analyze(np.asarray(audio), int(sr))
    verdict = "PASS" if float(result.score) >= float(threshold) else "RISK"
    return result, verdict


def mic_chunks(
    *,
    seconds: float = DEFAULT_SECONDS,
    window_s: float = DEFAULT_WINDOW_S,
    sr: int = DEFAULT_SR,
) -> Iterator[np.ndarray]:
    """Yield mono float64 windows from the default input (YOUR mic).

    ``seconds <= 0`` means run until the caller stops iterating
    (Ctrl-C in the CLI). Never selects a device other than the default.
    """
    sd = load_sounddevice()
    n_win = max(1, int(float(window_s) * int(sr)))
    n_total: int | None
    if seconds is not None and float(seconds) > 0:
        n_total = max(n_win, int(float(seconds) * int(sr)))
    else:
        n_total = None
    collected = 0
    while True:
        if n_total is not None and collected >= n_total:
            break
        frames = n_win
        if n_total is not None:
            frames = min(n_win, n_total - collected)
        try:
            rec = sd.rec(frames, samplerate=int(sr), channels=1, dtype="float32")
            sd.wait()
        except Exception as exc:  # noqa: BLE001 — surface device errors
            raise TetherError(f"microphone capture failed: {exc}") from exc
        collected += frames
        yield np.asarray(rec, dtype=np.float64).reshape(-1)


def run_listen(
    chunks: Iterable[np.ndarray],
    *,
    sr: int = DEFAULT_SR,
    threshold: float = DEFAULT_THRESHOLD,
    as_json: bool = False,
    out=None,
) -> tuple[int, float | None, str | None]:
    """Score each window, print PASS/RISK. Returns (n, last_score, last_verdict)."""
    out = sys.stdout if out is None else out
    n = 0
    last_score: float | None = None
    last_verdict: str | None = None
    for audio in chunks:
        result, verdict = score_window(audio, sr, threshold=threshold)
        last_score = float(result.score)
        last_verdict = verdict
        n += 1
        if as_json:
            payload = result.to_dict()
            payload["window"] = n
            payload["verdict"] = verdict
            payload["threshold"] = float(threshold)
            out.write(json.dumps(payload, indent=2))
            out.write("\n")
        else:
            out.write(
                f"window {n}  score={result.score:.3f}  {verdict}  "
                f"threshold={float(threshold):.3f}\n"
            )
            if result.reason_codes:
                out.write("  codes: " + ", ".join(result.reason_codes) + "\n")
        out.flush()
    return n, last_score, last_verdict


def listen_cli(
    *,
    seconds: float = DEFAULT_SECONDS,
    window_s: float = DEFAULT_WINDOW_S,
    sr: int = DEFAULT_SR,
    threshold: float = DEFAULT_THRESHOLD,
    gate: bool = False,
    as_json: bool = False,
    chunks_factory: Callable[..., Iterable[np.ndarray]] | None = None,
    out=None,
    err=None,
) -> int:
    """CLI body. ``chunks_factory`` is injected by tests (mocked mic)."""
    out = sys.stdout if out is None else out
    err = sys.stderr if err is None else err
    factory = chunks_factory or mic_chunks
    try:
        chunks = factory(seconds=seconds, window_s=window_s, sr=sr)
        n, last_score, last_verdict = run_listen(
            chunks, sr=sr, threshold=threshold, as_json=as_json, out=out
        )
    except TetherError as exc:
        err.write(f"error: {exc}\n")
        return 2
    except KeyboardInterrupt:
        out.write("\nstopped (YOUR mic; samples were not retained)\n")
        return 0
    if n == 0:
        err.write("error: no windows captured\n")
        return 2
    out.write(
        f"listen done  windows={n}  last={last_verdict}  "
        f"score={last_score:.3f}\n"
    )
    if gate and last_verdict == "RISK":
        err.write("gate: last window below threshold (RISK)\n")
        return 1
    return 0
