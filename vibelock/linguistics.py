"""Experimental linguistic proxies. Not speech-to-text.

These checks measure envelope rhythm, pause spacing, and spectral
transition size. They do not transcribe words, identify a language, or
claim a published linguistic model. Every note says so.

A subcheck that lacks pulses, pauses, or duration does not emit a
reason code and does not enter the score. That is fail-closed: missing
evidence is insufficient, not a pass and not a deepfake.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from vibelock import dsp
from vibelock.scoring import (
    LINGUISTIC_PAUSE_FLAT,
    LINGUISTIC_RHYTHM_METRONOME,
    LINGUISTIC_TRANSITION_FROZEN,
    CheckResult,
    clip01,
    logistic_score,
)

MIN_DURATION_S = 0.45
_HOP_S = 0.01

EXPERIMENTAL = "Experimental heuristic (not speech-to-text, not a language ID)."


def _zcr(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=np.float64)
    if x.size < 2:
        return 0.0
    signs = np.sign(x)
    signs[signs == 0.0] = 1.0
    return float(np.mean(signs[1:] * signs[:-1] < 0.0))


def speech_gate(audio: np.ndarray, sr: int) -> tuple[bool, str]:
    """True only when the clip is long enough and speech-like for these proxies."""
    x = dsp.as_mono_float(audio)
    if sr <= 0 or x.size < 8:
        return False, "No usable audio. Linguistics channel left insufficient."
    dur = x.size / float(sr)
    if dur < MIN_DURATION_S:
        return False, (
            f"Clip is {dur:.2f}s. Linguistics needs at least {MIN_DURATION_S:.2f}s; "
            "channel left insufficient."
        )
    if dsp.rms(x) < 1e-3:
        return False, "Audio is near silence. Linguistics channel left insufficient."
    z = _zcr(x)
    if z < 0.008 or z > 0.35:
        return False, (
            "Zero-crossing rate is outside the speech-like band this heuristic uses. "
            "Linguistics channel left insufficient."
        )
    return True, ""


def _envelope(audio: np.ndarray, sr: int) -> np.ndarray:
    return dsp.rms_envelope(audio, sr, hop_ms=_HOP_S * 1000.0)


def _peak_intervals(env: np.ndarray) -> np.ndarray:
    if env.size < 5:
        return np.zeros(0, dtype=np.float64)
    peak = float(np.max(env))
    if peak <= 1e-8:
        return np.zeros(0, dtype=np.float64)
    thr = 0.45 * peak
    peaks: list[int] = []
    for i in range(1, int(env.size) - 1):
        if env[i] >= env[i - 1] and env[i] > env[i + 1] and env[i] >= thr:
            if peaks and (i - peaks[-1]) * _HOP_S < 0.08:
                if env[i] > env[peaks[-1]]:
                    peaks[-1] = i
                continue
            peaks.append(i)
    if len(peaks) < 3:
        return np.zeros(0, dtype=np.float64)
    return np.diff(np.asarray(peaks, dtype=np.float64)) * _HOP_S


def _modulation_peak(env: np.ndarray) -> tuple[float, float]:
    """Return (peak_hz, peak_to_median) inside 2–8 Hz. (0, 0) if too short."""
    if env.size < 16:
        return 0.0, 0.0
    centered = env - float(np.mean(env))
    window = np.hanning(centered.size)
    spec = np.abs(np.fft.rfft(centered * window))
    freqs = np.fft.rfftfreq(centered.size, d=_HOP_S)
    band = (freqs >= 2.0) & (freqs <= 8.0)
    if not np.any(band):
        return 0.0, 0.0
    sl = spec[band]
    fr = freqs[band]
    idx = int(np.argmax(sl))
    med = float(np.median(sl)) + 1e-12
    return float(fr[idx]), float(sl[idx] / med)


def rhythm_metrics(audio: np.ndarray, sr: int) -> dict[str, float]:
    env = _envelope(audio, sr)
    peak_hz, ratio = _modulation_peak(env)
    intervals = _peak_intervals(env)
    if intervals.size:
        cv = float(np.std(intervals) / (np.mean(intervals) + 1e-9))
    else:
        cv = 0.0
    dyn = float(np.max(env) / (np.median(env) + 1e-8)) if env.size else 0.0
    return {
        "syllable_hz": peak_hz,
        "syllable_peak_ratio": ratio,
        "interval_cv": cv,
        "n_intervals": float(intervals.size),
        "envelope_dyn": dyn,
    }


def check_rhythm(audio: np.ndarray, sr: int) -> CheckResult | None:
    """Score syllable-rate regularity only when energy pulses exist.

    A steady voiced tone has no syllable grid. That is insufficient, not
    a synthetic-speech verdict.
    """
    m = rhythm_metrics(audio, sr)
    # A strong 2–8 Hz peak with several pulses. Steady voicing (low peak
    # ratio) is not a syllable grid and is left unscored.
    pulsed = m["n_intervals"] >= 4.0 and m["syllable_peak_ratio"] >= 4.0
    if not pulsed:
        return None
    cv = m["interval_cv"]
    ratio = m["syllable_peak_ratio"]
    # Natural-ish spacing sits away from a metronome (very low CV + one peak).
    cv_score = logistic_score(cv, good=0.18, bad=0.02)
    score = clip01(cv_score)
    code = None
    if ratio >= 5.0 and cv < 0.07 and m["n_intervals"] >= 4.0:
        code = LINGUISTIC_RHYTHM_METRONOME
        score = min(score, 0.32)
    return CheckResult(
        name="syllable_rhythm",
        score=score,
        reason_code=code,
        metrics=m,
        note=EXPERIMENTAL + " 2–8 Hz envelope peak and spacing of energy pulses.",
    )


def pause_metrics(audio: np.ndarray, sr: int) -> dict[str, float]:
    env = _envelope(audio, sr)
    if env.size < 8:
        return {"n_pauses": 0.0, "pause_cv": 0.0, "pause_mean_s": 0.0}
    thr = 0.12 * float(np.max(env))
    silent = env < thr
    pauses: list[float] = []
    run = 0
    for flag in silent:
        if flag:
            run += 1
        elif run:
            dur = run * _HOP_S
            if dur >= 0.08:
                pauses.append(dur)
            run = 0
    if run:
        dur = run * _HOP_S
        if dur >= 0.08:
            pauses.append(dur)
    if len(pauses) < 2:
        cv = 0.0
        mean = float(pauses[0]) if pauses else 0.0
    else:
        arr = np.asarray(pauses, dtype=np.float64)
        cv = float(np.std(arr) / (np.mean(arr) + 1e-9))
        mean = float(np.mean(arr))
    return {"n_pauses": float(len(pauses)), "pause_cv": cv, "pause_mean_s": mean}


def check_pauses(audio: np.ndarray, sr: int) -> CheckResult | None:
    m = pause_metrics(audio, sr)
    if m["n_pauses"] < 3.0:
        return None
    cv = m["pause_cv"]
    score = logistic_score(cv, good=0.35, bad=0.04)
    code = None
    if cv < 0.06:
        code = LINGUISTIC_PAUSE_FLAT
        score = min(score, 0.34)
    return CheckResult(
        name="pause_structure",
        score=clip01(score),
        reason_code=code,
        metrics=m,
        note=EXPERIMENTAL + " Coefficient of variation of silence runs ≥ 80 ms.",
    )


def transition_metrics(audio: np.ndarray, sr: int) -> dict[str, float]:
    frames, n_win, _hop = dsp.frame_signal(audio, sr, frame_ms=25.0, hop_ms=10.0)
    if frames.shape[0] < 6:
        return {"transition_median": 0.0, "frozen_frac": 0.0, "n_deltas": 0.0}
    nfft = dsp.next_pow2(n_win)
    mag = np.abs(np.fft.rfft(frames, n=nfft))
    mag = mag / (np.linalg.norm(mag, axis=1, keepdims=True) + 1e-12)
    deltas = np.linalg.norm(np.diff(mag, axis=0), axis=1)
    med = float(np.median(deltas))
    frozen = float(np.mean(deltas < 0.02))
    return {
        "transition_median": med,
        "frozen_frac": frozen,
        "n_deltas": float(deltas.size),
    }


def check_transition(audio: np.ndarray, sr: int) -> CheckResult | None:
    m = transition_metrics(audio, sr)
    if m["n_deltas"] < 8.0:
        return None
    med = m["transition_median"]
    # Normalized spectral flux. A locked tone sits near 0; voiced cartoons
    # sit higher. The unflagged score is capped: this is not a certainty.
    score = min(0.75, logistic_score(med, good=0.07, bad=0.012))
    code = None
    if med < 0.02:
        code = LINGUISTIC_TRANSITION_FROZEN
        score = min(score, 0.30)
    return CheckResult(
        name="linguistic_transition",
        score=clip01(score),
        reason_code=code,
        metrics=m,
        note=EXPERIMENTAL + " Median frame-to-frame normalized spectral flux (timbre motion, not phonemes).",
    )


def analyze_linguistics(audio: np.ndarray, sr: int) -> tuple[list[CheckResult], dict[str, Any]]:
    """Return checks plus a channel meta dict. Empty checks means insufficient."""
    ok, why = speech_gate(audio, sr)
    if not ok:
        return [], {
            "status": "insufficient",
            "evidence": "none",
            "note": EXPERIMENTAL + " " + why,
        }
    checks: list[CheckResult] = []
    rhythm = check_rhythm(audio, sr)
    pauses = check_pauses(audio, sr)
    transition = check_transition(audio, sr)
    if rhythm is not None:
        checks.append(rhythm)
    if pauses is not None:
        checks.append(pauses)
    if transition is not None:
        checks.append(transition)
    if not checks:
        return [], {
            "status": "insufficient",
            "evidence": "none",
            "note": (
                EXPERIMENTAL
                + " Speech-like audio, but no syllable pulses, pause runs, or "
                "transition frames long enough to score."
            ),
        }
    omitted: list[str] = []
    if rhythm is None:
        omitted.append("rhythm (no syllable-like energy pulses)")
    if pauses is None:
        omitted.append("pauses (fewer than 3 silence runs)")
    note = EXPERIMENTAL + " Fired: " + ", ".join(c.name for c in checks) + "."
    if omitted:
        note += " Not scored: " + "; ".join(omitted) + "."
    return checks, {
        "status": "fired",
        "evidence": "experimental",
        "note": note,
    }
