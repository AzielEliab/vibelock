"""VibeLock: physics + A/V deepfake detection.

July 2026 whitepaper (speech physics) and September 2026 A/V engine
by Aziel Eliab.

VibeLock asks whether media is physically consistent with a real vocal
tract, a real camera exposure, and — when both are present — a mouth
that produced the waveform. Dual-channel vibration, audio-only forensics,
spatial/temporal image-video artifacts, and pitch/phase shifts all feed
one score.

This is a media authenticity advisory, not courtroom proof.

Sound can be forged. Pixels can be forged. Physics is harder to fake.
"""

from __future__ import annotations

__version__ = "0.3.0"
__author__ = "Aziel Eliab"

from vibelock.scoring import AnalysisResult, CheckResult, analyze

__all__ = ["AnalysisResult", "CheckResult", "analyze", "__version__"]
