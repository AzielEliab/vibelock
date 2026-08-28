#!/usr/bin/env python3
"""Generate a synthetic dual-channel pair and run VibeLock on it.

Uses vibelock.synth.make_pair (not a recorded human), writes WAVs, runs
analyze, and prints the score plus reason codes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vibelock.io import write_wav
from vibelock.scoring import analyze, format_human
from vibelock.synth import make_pair


def main() -> int:
    out = Path(__file__).resolve().parent / "_out"
    out.mkdir(exist_ok=True)
    pair = make_pair(duration_s=1.2, sr=16000, f0=120.0, seed=202607)
    air = out / "air.wav"
    vib = out / "vibration.wav"
    write_wav(air, pair.audio, pair.sr)
    write_wav(vib, pair.vibration, pair.sr)

    print(f"wrote {air}")
    print(f"wrote {vib}")
    print("baseline: synthetic physically-plausible pair, not a human recording")
    print()

    result = analyze(pair.audio, pair.sr, vibration=pair.vibration)
    print(format_human(result))
    print()
    print(
        json.dumps(
            {
                "score": result.score,
                "mode": result.mode,
                "reason_codes": result.reason_codes,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
