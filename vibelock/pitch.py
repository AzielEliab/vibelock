"""Unnatural audio pitch and phase-shift detectors.

Talking-head and TTS deepfakes often leave a source that is not a
glottis: octave jumps, robotic flat F0, formants that ignore F0, and
phase-vocoder time-stretch. These checks sit next to the existing
Hilbert / formant forensic battery.
"""

from __future__ import annotations

import numpy as np
from scipy import signal

from vibelock import dsp
from vibelock.scoring import (
    FORMANT_PITCH_DECOUPLE,
    PHASE_SHIFT_UNNATURAL,
    PITCH_JUMP,
    PITCH_OVERFLAT,
    CheckResult,
    clip01,
    logistic_score,
)


def f0_track(audio: np.ndarray, sr: int, hop_ms: float = 10.0, frame_ms: float = 40.0) -> np.ndarray:
    """Per-frame autocorrelation F0 (Hz). 0 = unvoiced."""
    x = dsp.as_mono_float(audio)
    frames, _n_win, _hop = dsp.frame_signal(x, sr, frame_ms=frame_ms, hop_ms=hop_ms, window="hann")
    out = np.zeros(frames.shape[0], dtype=np.float64)
    for i, fr in enumerate(frames):
        if dsp.rms(fr) < 1e-4:
            continue
        out[i] = dsp.estimate_f0(fr, sr)
    return out


def _voiced(track: np.ndarray) -> np.ndarray:
    return track[(track > 60.0) & (track < 400.0)]


def check_pitch(audio: np.ndarray, sr: int) -> CheckResult:
    """Contour jumps and robotic flatness."""
    track = f0_track(audio, sr)
    voiced = _voiced(track)
    if voiced.size < 6:
        return CheckResult(
            "pitch",
            0.55,
            None,
            {"n_voiced": float(voiced.size)},
            "Too little voicing to judge pitch.",
        )
    # Semitone steps between consecutive voiced frames (ignore unvoiced gaps).
    steps: list[float] = []
    prev = 0.0
    for f in track:
        if 60.0 < f < 400.0 and 60.0 < prev < 400.0:
            steps.append(abs(12.0 * np.log2(f / prev)))
        prev = f
    if not steps:
        max_st = 0.0
        n_big = 0
    else:
        arr = np.asarray(steps, dtype=np.float64)
        max_st = float(np.max(arr))
        n_big = int(np.count_nonzero(arr > 6.0))
    # Flatness: coefficient of variation of voiced F0.
    cv = float(np.std(voiced) / (np.mean(voiced) + 1e-9))
    jump_score = logistic_score(max_st, good=1.8, bad=9.0)
    if n_big:
        jump_score = min(jump_score, logistic_score(float(n_big), good=0.0, bad=6.0))
    # Natural speech CV is typically a few percent plus vibrato; robots sit near 0.
    flat_score = logistic_score(cv, good=0.035, bad=0.004)
    # Also penalize wild random F0 (unstable_formants attack).
    wild_score = logistic_score(cv, good=0.12, bad=0.45)
    score = clip01(min(jump_score, max(flat_score, 0.12), wild_score))
    code = None
    if max_st > 7.0 and n_big >= 1:
        code = PITCH_JUMP
        score = min(score, 0.22)
    elif cv < 0.008 and voiced.size > 10:
        code = PITCH_OVERFLAT
        score = min(score, 0.28)
    return CheckResult(
        name="pitch",
        score=score,
        reason_code=code,
        metrics={
            "max_semitone_jump": max_st,
            "n_big_jumps": float(n_big),
            "f0_cv": cv,
            "f0_median": float(np.median(voiced)),
            "n_voiced": float(voiced.size),
        },
        note="Autocorrelation F0 contour: octave jumps and robotic flatness.",
    )


def check_formant_pitch(audio: np.ndarray, sr: int) -> CheckResult:
    """Source–filter coupling: F1 should not teleport independently of F0."""
    tracks = dsp.formant_tracks(audio, sr)
    f0 = f0_track(audio, sr)
    if tracks.size == 0 or f0.size == 0:
        return CheckResult("formant", 0.5, None, {}, "No formant/F0 tracks.")
    n = min(tracks.shape[0], f0.size)
    f1 = tracks[:n, 0]
    f0 = f0[:n]
    ok = np.isfinite(f1) & (f0 > 60.0) & (f0 < 400.0)
    if np.count_nonzero(ok) < 8:
        return CheckResult(
            "formant",
            0.55,
            None,
            {"n_coupled": float(np.count_nonzero(ok))},
            "Not enough voiced formant frames.",
        )
    # Residual of F1 after a linear fit on F0 — TTS often draws them independently.
    x = f0[ok]
    y = f1[ok]
    A = np.vstack([x, np.ones_like(x)]).T
    coeff, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - (coeff[0] * x + coeff[1])
    rel = float(np.std(resid) / (np.std(y) + 1e-9))
    # Also raw F1 jump vs F0 jump correlation (should not be ~0 with huge F1).
    df1 = np.abs(np.diff(y))
    df0 = np.abs(np.diff(x))
    if df1.size > 4 and float(np.std(df1)) > 1e-6 and float(np.std(df0)) > 1e-6:
        corr = float(np.corrcoef(df1, df0)[0, 1])
        if not np.isfinite(corr):
            corr = 0.0
    else:
        corr = 0.0
    score = clip01(min(logistic_score(rel, good=0.45, bad=0.95), logistic_score(abs(corr), good=0.25, bad=0.02)))
    code = FORMANT_PITCH_DECOUPLE if rel > 0.88 else None
    if code:
        score = min(score, 0.34)
    return CheckResult(
        name="formant",
        score=score,
        reason_code=code,
        metrics={"f1_f0_resid_rel": rel, "df1_df0_corr": corr},
        note="F1 residual after a linear F0 fit (source–filter decoupling).",
    )


def check_phase_shift(audio: np.ndarray, sr: int) -> CheckResult:
    """Phase-vocoder / time-stretch: horizontal phase locking across frames."""
    x = dsp.as_mono_float(audio)
    if x.size < int(0.12 * sr):
        return CheckResult("phase_continuity", 0.55, None, {}, "Too short for STFT phase.")
    nper = 256
    _f, _t, zxx = signal.stft(x, fs=sr, nperseg=nper, noverlap=nper // 2)
    phase = np.unwrap(np.angle(zxx), axis=1)
    # Instantaneous frequency per bin: d(phase)/dt should be stable for a
    # sinusoid and ragged for natural speech. Vocoder stretch over-smoothes.
    dphi = np.diff(phase, axis=1)
    # Variance of IF across time, median across speech-ish bins (80–2000 Hz).
    freqs = np.fft.rfftfreq(nper, 1.0 / sr)
    band = (freqs >= 80.0) & (freqs <= 2000.0)
    if not np.any(band) or dphi.shape[1] < 4:
        return CheckResult("phase_continuity", 0.5, None, {}, "STFT too short.")
    if_var = np.var(dphi[band], axis=1)
    med_var = float(np.median(if_var))
    # Time-stretch also creates a ridge of near-zero IF variance.
    frac_flat = float(np.mean(if_var < 0.15))
    score = clip01(min(logistic_score(med_var, good=1.2, bad=0.05), logistic_score(frac_flat, good=0.15, bad=0.70)))
    code = PHASE_SHIFT_UNNATURAL if (med_var < 0.12 and frac_flat > 0.45) else None
    if code:
        score = min(score, 0.30)
    return CheckResult(
        name="phase_continuity",
        score=score,
        reason_code=code,
        metrics={"stft_if_var": med_var, "frac_flat_bins": frac_flat},
        note="STFT instantaneous-frequency variance (phase-vocoder stretch).",
    )


def analyze_pitch(audio: np.ndarray, sr: int) -> list[CheckResult]:
    audio = dsp.as_mono_float(audio)
    return [
        check_pitch(audio, sr),
        check_formant_pitch(audio, sr),
        check_phase_shift(audio, sr),
    ]
