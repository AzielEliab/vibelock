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
# Image / video / A/V deepfake engine
FREQ_FINGERPRINT = "FREQ_FINGERPRINT"
NOISE_INCONSISTENT = "NOISE_INCONSISTENT"
BLOCK_ARTIFACT = "BLOCK_ARTIFACT"
CHROMA_INCONSISTENT = "CHROMA_INCONSISTENT"
BLEND_BOUNDARY = "BLEND_BOUNDARY"
LIGHTING_INCONSISTENT = "LIGHTING_INCONSISTENT"
TEMPORAL_FLICKER = "TEMPORAL_FLICKER"
MOTION_INCONSISTENT = "MOTION_INCONSISTENT"
IDENTITY_FLICKER = "IDENTITY_FLICKER"
INTERP_ARTIFACT = "INTERP_ARTIFACT"
PITCH_JUMP = "PITCH_JUMP"
PITCH_OVERFLAT = "PITCH_OVERFLAT"
FORMANT_PITCH_DECOUPLE = "FORMANT_PITCH_DECOUPLE"
PHASE_SHIFT_UNNATURAL = "PHASE_SHIFT_UNNATURAL"
AV_SYNC_FAIL = "AV_SYNC_FAIL"

DUAL_WEIGHTS: dict[str, float] = {
    "coherence": 0.30,
    "transfer": 0.25,
    "phase_latency": 0.20,
    "decay": 0.15,
    "forensic": 0.10,
}

AUDIO_WEIGHTS: dict[str, float] = {
    "spectral": 0.16,
    "phase_continuity": 0.20,
    "formant": 0.20,
    "decay": 0.14,
    "temporal": 0.12,
    "buzz": 0.07,
    "pitch": 0.11,
}

IMAGE_WEIGHTS: dict[str, float] = {
    "spatial_freq": 0.22,
    "noise": 0.18,
    "block": 0.12,
    "chroma": 0.16,
    "blend": 0.16,
    "lighting": 0.16,
}

VIDEO_WEIGHTS: dict[str, float] = {
    "spatial_freq": 0.10,
    "noise": 0.08,
    "block": 0.05,
    "chroma": 0.07,
    "blend": 0.07,
    "lighting": 0.08,
    "flicker": 0.16,
    "motion": 0.15,
    "identity": 0.14,
    "interp": 0.10,
}

AV_WEIGHTS: dict[str, float] = {
    "spectral": 0.04,
    "phase_continuity": 0.05,
    "formant": 0.05,
    "decay": 0.03,
    "temporal": 0.03,
    "buzz": 0.02,
    "pitch": 0.06,
    "spatial_freq": 0.07,
    "noise": 0.05,
    "block": 0.03,
    "chroma": 0.05,
    "blend": 0.05,
    "lighting": 0.05,
    "flicker": 0.08,
    "motion": 0.08,
    "identity": 0.07,
    "interp": 0.04,
    "av_sync": 0.15,
}

MODE_WEIGHTS: dict[str, dict[str, float]] = {
    "dual_channel": DUAL_WEIGHTS,
    "audio_only": AUDIO_WEIGHTS,
    "image": IMAGE_WEIGHTS,
    "video": VIDEO_WEIGHTS,
    "av": AV_WEIGHTS,
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


def verdict_of(score: float, reason_codes: Iterable[str], mode: str) -> str:
    """Map a score onto deepfake / consistent / inconclusive.

    Thresholds are engineering defaults for synthetic fixtures, not a
    published operating point.
    """
    codes = list(reason_codes)
    visual = mode in {"image", "video", "av"}
    if visual and score < 0.42 and codes:
        return "deepfake"
    if score >= 0.58 and not codes:
        return "consistent"
    if score >= 0.55:
        return "consistent"
    if score < 0.42 and codes:
        return "deepfake" if visual else "inconsistent"
    return "inconclusive"


@dataclass
class AnalysisResult:
    """Top-level VibeLock output (no raw media is retained)."""

    score: float
    mode: str
    reason_codes: list[str]
    checks: list[CheckResult]
    sample_rate: int
    n_samples: int
    notes: list[str] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)
    n_frames: int = 0
    fps: float = 0.0
    verdict: str = ""

    def to_dict(self) -> dict[str, Any]:
        verdict = self.verdict or verdict_of(self.score, self.reason_codes, self.mode)
        return {
            "score": float(self.score),
            "mode": self.mode,
            "verdict": verdict,
            "reason_codes": list(self.reason_codes),
            "checks": [c.to_dict() for c in self.checks],
            "sample_rate": int(self.sample_rate),
            "n_samples": int(self.n_samples),
            "n_frames": int(self.n_frames),
            "fps": float(self.fps),
            "signals": list(self.signals),
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
    signals: Iterable[str] | None = None,
    n_frames: int = 0,
    fps: float = 0.0,
) -> AnalysisResult:
    checks = list(checks)
    weights = MODE_WEIGHTS.get(mode) or AUDIO_WEIGHTS
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
    # Smoking-gun cues reject altered media. Support codes alone do not
    # (a translating blob can look like "motion roughness").
    smoking = {
        FREQ_FINGERPRINT,
        NOISE_INCONSISTENT,
        BLEND_BOUNDARY,
        CHROMA_INCONSISTENT,
        TEMPORAL_FLICKER,
        IDENTITY_FLICKER,
        INTERP_ARTIFACT,
        PITCH_JUMP,
        PHASE_SHIFT_UNNATURAL,
        AV_SYNC_FAIL,
    }
    n_smoke = sum(1 for c in ordered if c in smoking)
    if mode in {"image", "video", "av"} and n_smoke >= 2:
        score = min(score, 0.26)
    elif mode in {"image", "video", "av"} and n_smoke == 1:
        score = min(score, 0.36)
    result = AnalysisResult(
        score=score,
        mode=mode,
        reason_codes=ordered,
        checks=checks,
        sample_rate=sample_rate,
        n_samples=n_samples,
        notes=list(notes or []),
        signals=list(signals or []),
        n_frames=int(n_frames),
        fps=float(fps),
    )
    result.verdict = verdict_of(result.score, result.reason_codes, result.mode)
    return result


def _mode_for(
    has_audio: bool,
    has_vib: bool,
    has_image: bool,
    has_video: bool,
) -> str:
    if has_video and has_audio:
        return "av"
    if has_video:
        return "video"
    if has_image and has_audio:
        return "av"
    if has_image:
        return "image"
    if has_vib:
        return "dual_channel"
    return "audio_only"


def analyze(
    audio: np.ndarray | None = None,
    sr: int | None = None,
    vibration: np.ndarray | None = None,
    *,
    image: np.ndarray | None = None,
    frames: np.ndarray | None = None,
    fps: float | None = None,
) -> AnalysisResult:
    """Multi-signal entry point: audio, vibration, stills, and frame stacks.

    Audio-only and dual-channel callers keep the original positional
    signature. Image / video / A/V are keyword-only. Raw media is not
    retained on the result.
    """
    from vibelock.dsp import as_mono_float, rms
    from vibelock.dual_channel import analyze_dual
    from vibelock.forensic import analyze_audio

    notes: list[str] = []
    extra: list[str] = []
    checks: list[CheckResult] = []
    signals: list[str] = []
    n_samples = 0
    sample_rate = int(sr or 0)
    n_frames = 0
    rate = float(fps or 0.0)

    audio_v = None
    if audio is not None:
        audio_v = as_mono_float(audio)
        n_samples = int(audio_v.size)
        if sample_rate <= 0:
            sample_rate = 16000
        checks.extend(analyze_audio(audio_v, sample_rate))
        signals.append("audio")

    has_vib = False
    if vibration is not None and audio_v is not None:
        vib = as_mono_float(vibration)
        if vib.size < int(0.08 * sample_rate) or rms(vib) < 1e-6:
            notes.append("Vibration missing or unusable; falling back to audio-only.")
            extra.append(VIBRATION_UNUSABLE)
        else:
            n = min(audio_v.size, vib.size)
            checks.extend(analyze_dual(audio_v[:n], vib[:n], sample_rate))
            signals.append("physics")
            has_vib = True

    if image is not None:
        from vibelock.vision import analyze_image

        checks.extend(analyze_image(image))
        signals.append("spatial")

    if frames is not None:
        from vibelock.temporal import analyze_video

        stack_checks = analyze_video(frames, include_spatial=image is None)
        checks.extend(stack_checks)
        signals.append("temporal")
        if image is None:
            signals.append("spatial")
        n_frames = int(np.asarray(frames).shape[0])
        if rate <= 0:
            rate = 25.0
        if audio_v is not None:
            from vibelock.avsync import analyze_av

            checks.extend(analyze_av(audio_v, sample_rate, frames, fps=rate))
            signals.append("av_sync")

    if not checks:
        raise ValueError("analyze() needs audio, image, or frames")

    # Deduplicate signal labels, stable order.
    seen_sig: set[str] = set()
    ordered_sig: list[str] = []
    for s in signals:
        if s not in seen_sig:
            seen_sig.add(s)
            ordered_sig.append(s)

    mode = _mode_for(
        audio_v is not None,
        has_vib,
        image is not None,
        frames is not None,
    )
    # Image + audio without frames: still use AV weights so both families count.
    if mode == "av" and frames is None and image is not None:
        notes.append("Still image plus audio: spatial + forensic, no temporal sync.")
    return combine(
        checks,
        mode,
        sample_rate or 0,
        n_samples,
        notes,
        extra,
        signals=ordered_sig,
        n_frames=n_frames,
        fps=rate,
    )


def format_human(result: AnalysisResult) -> str:
    codes = ", ".join(result.reason_codes) if result.reason_codes else "(none)"
    lines = [
        f"VibeLock authenticity score: {result.score:.3f}",
        f"Verdict: {result.verdict or verdict_of(result.score, result.reason_codes, result.mode)}",
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
