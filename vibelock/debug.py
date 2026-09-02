"""Local debug logs. Never sent anywhere.

Enable with ``VIBELOCK_DEBUG=1``. Output is stderr only. No telemetry.
"""

from __future__ import annotations

import os
import sys

_TRUE = {"1", "true", "yes", "on"}


def enabled() -> bool:
    raw = os.environ.get("VIBELOCK_DEBUG", "")
    return raw.strip().lower() in _TRUE


def log(msg: str) -> None:
    """Write a debug line to stderr when VIBELOCK_DEBUG=1. Never a network call."""
    if enabled():
        sys.stderr.write(f"vibelock debug: {msg}\n")
        sys.stderr.flush()
