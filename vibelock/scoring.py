"""Composite authenticity scoring and machine-readable reason codes.

Whitepaper § scoring: a probabilistic score in [0, 1] plus interpretable
reason codes. Thresholds here are *implementation defaults* chosen so
synthetic fixtures move the score in the documented direction. They are
not published operating points from a human listening study, and this
file invents no evaluation numbers or citations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

import numpy as np

# Reason codes listed in the whitepaper, plus a few that name phenomena
# the same document already describes (vocoder buzz, overly-flat phase,
# latency/drift, spectral unnaturalness).
COHERENCE_LOW = "COHERENCE_LOW"
COHERENCE_UNSTABLE = "COHERENCE_UNSTABLE"
PHASE_DISCONTINUITY = "PHASE_DISCONTINUITY"
PHASE_OVERFLAT = "PHASE_OVERFLAT"
LATENCY_OUT_OF_BOUNDS = "LATENCY_OUT_OF_BOUNDS"
DRIFT_EXCESSIVE = "DRIFT_EXCESSIVE"
TRANSFER_RESIDUAL_HIGH = "TRANSFER_RESIDUAL_HIGH"
DECAY_IMPLAUSIBLE = "DECAY_IMPLAUSIBLE"
FORMANT_UNSTABLE = "FORMANT_UNSTABLE"
TEMPORAL_SPLICE = "TEMPORAL_SPLICE"
SPECTRAL_UNNATURAL = "SPECTRAL_UNNATURAL"
VOCODER_BUZZ = "VOCODER_BUZZ"
VIBRATION_UNUSABLE = "VIBRATION_UNUSABLE"

DUAL_WEIGHTS: dict[str, float] = {
    "coherence": 0.30,
    "transfer": 0.25,
    "phase_latency": 0.20,
    "decay": 0.15,
    "forensic": 0.10,
}

AUDIO_WEIGHTS: dict[str, float] = {
    "spectral": 0.18,
    "phase_continuity": 0.22,
    "formant": 0.22,
    "decay": 0.16,
    "temporal": 0.14,
    "buzz": 0.08,
}


@dataclass
class CheckResult:
    """One physical test, a 0–1 subscore, and an optional reason code."""

    name: str
    score: float
    reason_code: str | None
    metrics: dict[str, float] = field(default_factory=dict)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": float(self.score),
            "reason_code": self.reason_code,
            "metrics": {k: float(v) for k, v in self.metrics.items()},
            "note": self.note,
        }


@dataclass
class AnalysisResult:
    """Top-level VibeLock output (no raw audio is retained)."""

    score: float
    mode: str
    reason_codes: list[str]
    checks: list[CheckResult]
    sample_rate: int
    n_samples: int
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": float(self.score),
            "mode": self.mode,
            "reason_codes": list(self.reason_codes),
            "checks": [c.to_dict() for c in self.checks],
            "sample_rate": int(self.sample_rate),
            "n_samples": int(self.n_samples),
            "notes": list(self.notes),
        }


def clip01(x: float) -> float:
    return float(min(1.0, max(0.0, x)))


def logistic_score(value: float, good: float, bad: float) -> float:
    """Map a scalar onto [0, 1]. ``good`` scores near 1, ``bad`` near 0.

    Uses a smoothstep between the two anchors so tests can sit clearly
    on either side without claiming a calibrated probability.
    """
    if good == bad:
        return 0.5
    t = (value - bad) / (good - bad)
    t = clip01(t)
    # Hermite smoothstep
    return float(t * t * (3.0 - 2.0 * t))


def combine(
    checks: Iterable[CheckResult],
    mode: str,
    sample_rate: int,
    n_samples: int,
    notes: list[str] | None = None,
    extra_codes: Iterable[str] | None = None,
) -> AnalysisResult:
    checks = list(checks)
    weights = DUAL_WEIGHTS if mode == "dual_channel" else AUDIO_WEIGHTS
    # Forensic dual-channel contribution is the mean of audio-only checks
    # that were attached with names in AUDIO_WEIGHTS.
    grouped: dict[str, list[float]] = {k: [] for k in weights}
    ungrouped: list[float] = []
    for c in checks:
        if c.name in grouped:
            grouped[c.name].append(c.score)
        elif mode == "dual_channel" and c.name in AUDIO_WEIGHTS:
            grouped["forensic"].append(c.score)
        else:
            ungrouped.append(c.score)

    num = 0.0
    den = 0.0
    for name, w in weights.items():
        vals = grouped.get(name) or []
        if not vals:
            continue
        num += w * float(np.mean(vals))
        den += w
    if ungrouped and den < 0.99:
        leftover = max(0.0, 1.0 - den)
        num += leftover * float(np.mean(ungrouped))
        den += leftover
    score = clip01(num / den if den > 0 else 0.0)

    codes: list[str] = []
    for c in checks:
        if c.reason_code:
            codes.append(c.reason_code)
    if extra_codes:
        codes.extend(extra_codes)
    # Stable unique order.
    seen: set[str] = set()
    ordered: list[str] = []
    for code in codes:
        if code not in seen:
            seen.add(code)
            ordered.append(code)
    return AnalysisResult(
        score=score,
        mode=mode,
        reason_codes=ordered,
        checks=checks,
        sample_rate=sample_rate,
        n_samples=n_samples,
        notes=list(notes or []),
    )


def analyze(
    audio: np.ndarray,
    sr: int,
    vibration: np.ndarray | None = None,
) -> AnalysisResult:
    """Run dual-channel analysis when vibration is present, else audio-only.

    This is the library-level entry point. The CLI is a thin wrapper.
    """
    from vibelock.dual_channel import analyze_dual
    from vibelock.forensic import analyze_audio
    from vibelock.dsp import as_mono_float, rms

    audio = as_mono_float(audio)
    notes: list[str] = []
    extra: list[str] = []
    if vibration is None:
        checks = analyze_audio(audio, sr)
        return combine(checks, "audio_only", sr, int(audio.size), notes)

    vib = as_mono_float(vibration)
    if vib.size < int(0.08 * sr) or rms(vib) < 1e-6:
        notes.append("Vibration missing or unusable; falling back to audio-only.")
        extra.append(VIBRATION_UNUSABLE)
        checks = analyze_audio(audio, sr)
        return combine(checks, "audio_only", sr, int(audio.size), notes, extra)

    n = min(audio.size, vib.size)
    dual_checks = analyze_dual(audio[:n], vib[:n], sr)
    # Supporting forensic evidence, down-weighted in combine().
    audio_checks = analyze_audio(audio[:n], sr)
    return combine(dual_checks + audio_checks, "dual_channel", sr, n, notes, extra)


def format_human(result: AnalysisResult) -> str:
    codes = ", ".join(result.reason_codes) if result.reason_codes else "(none)"
    lines = [
        f"VibeLock authenticity score: {result.score:.3f}",
        f"Mode: {result.mode}",
        f"Reason codes: {codes}",
        f"Sample rate: {result.sample_rate} Hz, samples: {result.n_samples}",
    ]
    if result.notes:
        for n in result.notes:
            lines.append(f"Note: {n}")
    lines.append("Checks:")
    for c in result.checks:
        flag = f" [{c.reason_code}]" if c.reason_code else ""
        lines.append(f"  - {c.name}: {c.score:.3f}{flag}")
    return "\n".join(lines)


def json_ready(obj: Mapping[str, Any] | AnalysisResult) -> Any:
    if isinstance(obj, AnalysisResult):
        return obj.to_dict()
    return obj
