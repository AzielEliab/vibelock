"""VibeLock: physical-consistency evaluation of speech audio.

July 2026 whitepaper implementation by Aziel Eliab.

VibeLock asks whether a recording is physically consistent with human vocal
vibration and biomechanical resonance. Dual-channel mode uses air audio plus
body-coupled vibration. Audio-only mode is a forensic risk assessment, not a
proof of liveness.

This is an audio authenticity advisory, not courtroom proof.

Sound can be forged. Physics is harder to fake.
"""

from __future__ import annotations

__version__ = "0.2.0"
__author__ = "Aziel Eliab"

from vibelock.scoring import AnalysisResult, CheckResult, analyze

__all__ = ["AnalysisResult", "CheckResult", "analyze", "__version__"]
