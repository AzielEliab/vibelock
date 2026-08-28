"""VibeLock: physical-consistency evaluation of speech audio.

July 2026 whitepaper implementation by Aziel Eliab.

VibeLock asks whether a recording is physically consistent with human vocal
vibration and biomechanical resonance. Dual-channel mode uses air audio plus
body-coupled vibration. Audio-only mode is a forensic risk assessment, not a
proof of liveness.

Sound can be forged. Physics is harder to fake.
"""

from __future__ import annotations

from vibelock.scoring import AnalysisResult, CheckResult, analyze

__version__ = "0.1.0"
__author__ = "Aziel Eliab"
__all__ = ["AnalysisResult", "CheckResult", "analyze", "__version__"]
