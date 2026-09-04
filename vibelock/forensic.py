"""Audio-only forensic risk assessment.

Whitepaper mode 2: when body-coupled vibration is absent, VibeLock still
inspects spectral smoothness, phase continuity, formant stability,
resonance behavior, and temporal artifacts (splices, vocoder buzz,
overly-flat phase). This is a *risk assessment*, not a proof of liveness.
"""

from __future__ import annotations

import numpy as np

from vibelock import dsp
from vibelock.scoring import (
    DECAY_IMPLAUSIBLE,
    FORMANT_UNSTABLE,
    PHASE_DISCONTINUITY,
    PHASE_OVERFLAT,
    SPECTRAL_UNNATURAL,
    TEMPORAL_SPLICE,
    VOCODER_BUZZ,
    CheckResult,
    clip01,
    logistic_score,
)


def check_spectral(audio: np.ndarray, sr: int) -> CheckResult:
    stats = dsp.spectral_smoothness(audio, sr)
    fine = stats["fine_var"]
    # Natural harmonic speech has moderate fine-structure variance.
    # Zero-phase / over-smoothed vocoder: very low. White-noise: very high.
    # Score peaks in a mid band and falls off both sides.
    low = logistic_score(fine, good=0.08, bad=0.005)
    high = logistic_score(fine, good=0.25, bad=1.60)
    score = clip01(min(low, high))
    code = None
    if fine < 0.012 or fine > 1.20:
        code = SPECTRAL_UNNATURAL
        score = min(score, 0.40)
    return CheckResult(
        name="spectral",
        score=score,
        reason_code=code,
        metrics=stats,
        note="Log-spectral fine structure after a formant-scale envelope.",
    )


def check_phase_continuity(audio: np.ndarray, sr: int) -> CheckResult:
    jump = dsp.phase_jump_rate(audio, sr)
    resid = dsp.phase_residual_variance(audio, sr)
    # Dense irregular Hilbert jumps → discontinuity.
    # Tiny residual IF variance with non-tiny energy → overly flat phase.
    jump_score = logistic_score(jump, good=8.0, bad=28.0)
    # Residual variance of IF in Hz^2. Natural jitter is thousands here
    # because of glottal FM; overly-flat vocoder phase sits near zero.
    flat_score = logistic_score(resid, good=400.0, bad=8.0)
    chaotic_score = logistic_score(resid, good=3.0e4, bad=2.5e6)
    score = clip01(min(jump_score, max(flat_score, 0.15), chaotic_score))
    code = None
    if jump > 12.0:
        code = PHASE_DISCONTINUITY
        score = min(score, 0.35)
    elif resid < 20.0:
        code = PHASE_OVERFLAT
        score = min(score, 0.40)
    return CheckResult(
        name="phase_continuity",
        score=score,
        reason_code=code,
        metrics={"phase_jump_rate": jump, "if_residual_var": resid},
        note="Hilbert phase jumps and detrended instantaneous-frequency variance.",
    )


def check_formant(audio: np.ndarray, sr: int) -> CheckResult:
    tracks = dsp.formant_tracks(audio, sr)
    st = dsp.formant_stability(tracks)
    med = st["median_jump_hz"]
    p95 = st["p95_jump_hz"]
    # Median jump is the robust cue. LPC peak swapping inflates p95 even
    # on a stationary three-resonator cartoon; that is a tracker artifact,
    # not vocal-tract teleportation.
    score = logistic_score(med, good=50.0, bad=150.0)
    score = clip01(score)
    code = None
    if med > 110.0:
        code = FORMANT_UNSTABLE
        score = min(score, 0.35)
    return CheckResult(
        name="formant",
        score=score,
        reason_code=code,
        metrics=st,
        note="LPC peak tracks (formant-ish), frame-to-frame stability.",
    )


def check_decay(audio: np.ndarray, sr: int) -> CheckResult:
    # Same anatomical decay test as dual-channel; audio-only still cares.
    from vibelock.dual_channel import check_decay as _decay

    return _decay(audio, sr)


def check_temporal(audio: np.ndarray, sr: int) -> CheckResult:
    flux = dsp.spectral_flux(audio, sr)
    env = dsp.rms_envelope(audio, sr, hop_ms=10.0)
    if env.size < 6:
        return CheckResult("temporal", 0.5, None, {}, "Too short to judge splices.")
    log_env = np.log(env + 1e-8)
    d_env = np.abs(np.diff(log_env))
    # A hard splice in the middle of energy produces a coincident RMS jump
    # *and* a spectral-flux spike, without a stop-gap (near-silence) before it.
    n = min(d_env.size, flux.size)
    if n < 4:
        return CheckResult("temporal", 0.5, None, {}, "Too short to judge splices.")
    d_env, flux = d_env[:n], flux[:n]
    env_body = env[:n]
    # Preceding-frame energy, to ignore true onsets from silence.
    prev_e = env_body
    flux_z = (flux - np.median(flux)) / (np.std(flux) + 1e-8)
    env_z = (d_env - np.median(d_env)) / (np.std(d_env) + 1e-8)
    coincident = (flux_z > 3.5) & (env_z > 3.5) & (prev_e > 0.08 * np.max(env))
    n_hits = int(np.count_nonzero(coincident))
    max_combo = float(np.max(flux_z + env_z)) if n else 0.0
    # Pulse-train frames already have combo z ~ 10. Hard splices go higher
    # *and* produce coincident RMS+flux hits.
    score = logistic_score(max_combo, good=12.0, bad=22.0)
    if n_hits:
        score = min(score, logistic_score(float(n_hits), good=0.0, bad=4.0))
    score = clip01(score)
    code = TEMPORAL_SPLICE if (n_hits >= 1 and max_combo > 12.0) else None
    if code:
        score = min(score, 0.35)
    return CheckResult(
        name="temporal",
        score=score,
        reason_code=code,
        metrics={
            "n_splice_hits": float(n_hits),
            "max_flux_env_z": max_combo,
            "p95_flux": float(np.percentile(flux, 95)),
        },
        note="Coincident RMS and spectral-flux spikes (splice-like).",
    )


def check_buzz(audio: np.ndarray, sr: int) -> CheckResult:
    mod = dsp.modulation_spectrum_peak(audio, sr, lo_hz=40.0, hi_hz=220.0)
    ratio = mod["peak_to_med"]
    f0 = dsp.estimate_f0(audio, sr)
    peak_hz = mod["peak_hz"]
    # A Hilbert-envelope peak at F0 is glottal pulsing, not vocoder hop.
    rel_f0 = abs(peak_hz - f0) / max(f0, 1.0) if f0 > 0 else 99.0
    rel_2p = abs(peak_hz - 2.0 * f0) / max(2.0 * f0, 1.0) if f0 > 0 else 99.0
    glottal = min(rel_f0, rel_2p) < 0.12
    metrics = {**mod, "f0_hz": float(f0), "rel_f0": float(rel_f0)}
    if glottal:
        return CheckResult(
            name="buzz",
            score=0.95,
            reason_code=None,
            metrics=metrics,
            note="Envelope peak matches estimated F0 (glottal, not hop buzz).",
        )
    score = logistic_score(ratio, good=6.0, bad=20.0)
    code = VOCODER_BUZZ if ratio > 12.0 else None
    if code:
        score = min(score, 0.40)
    return CheckResult(
        name="buzz",
        score=clip01(score),
        reason_code=code,
        metrics=metrics,
        note="Envelope modulation-spectrum peak off F0 in the vocoder-hop band.",
    )


def analyze_audio(audio: np.ndarray, sr: int) -> list[CheckResult]:
    """Run the audio-only forensic battery, including pitch / phase-shift."""
    from vibelock.pitch import check_phase_shift, check_pitch

    audio = dsp.as_mono_float(audio)
    checks = [
        check_spectral(audio, sr),
        check_phase_continuity(audio, sr),
        check_formant(audio, sr),
        check_decay(audio, sr),
        check_temporal(audio, sr),
        check_buzz(audio, sr),
        check_pitch(audio, sr),
    ]
    # Extra STFT phase-vocoder evidence, averaged into phase_continuity.
    checks.append(check_phase_shift(audio, sr))
    return checks
