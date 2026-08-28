"""Dual-channel physical tests (air audio + body-coupled vibration).

Whitepaper mode 1: synchronize, drift-correct, then evaluate time,
frequency, and phase consistency between the air microphone and a
jaw accelerometer / contact mic / IMU.

Checks implemented here:

* Vibration–audio magnitude-squared coherence in the coupling band
  (~80–2000 Hz) and the broader speech band (~80–4000 Hz).
* Transfer-function residual versus a *synthetic* bootstrap baseline
  (see ``vibelock.synth``; not a published human dataset).
* Phase / latency constraints: GCC-PHAT delay inside a causal window,
  bounded drift across windows.
* Resonance decay profiles on the air channel (anatomical vs reverb).
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from vibelock import dsp
from vibelock.scoring import (
    COHERENCE_LOW,
    COHERENCE_UNSTABLE,
    DECAY_IMPLAUSIBLE,
    DRIFT_EXCESSIVE,
    LATENCY_OUT_OF_BOUNDS,
    TRANSFER_RESIDUAL_HIGH,
    CheckResult,
    clip01,
    logistic_score,
)
from vibelock.synth import bootstrap_pairs

# Log-frequency grid shared by observed TFs and the bootstrap prior.
_TF_GRID: NDArray[np.float64] | None = None
_TF_MEAN: NDArray[np.float64] | None = None
_TF_STD: NDArray[np.float64] | None = None
_TF_MEMBERS: NDArray[np.float64] | None = None
_TF_SR: int | None = None


def _tf_grid() -> NDArray[np.float64]:
    global _TF_GRID
    if _TF_GRID is None:
        lo, hi = dsp.SPEECH_BAND_HZ
        _TF_GRID = np.geomspace(lo, hi, 64)
    return _TF_GRID


def _ensure_baseline(sr: int) -> None:
    """Lazy-build the synthetic transfer-function prior at ``sr``."""
    global _TF_MEAN, _TF_STD, _TF_MEMBERS, _TF_SR
    if _TF_MEMBERS is not None and _TF_SR == sr:
        return
    pairs = bootstrap_pairs(n_pairs=20, sr=sr, duration_s=0.8, seed=202607)
    grid = _tf_grid()
    rows: list[np.ndarray] = []
    for p in pairs:
        freqs, h, _c = dsp.transfer_function(p.vibration, p.audio, p.sr)
        rows.append(dsp.log_mag_on_grid(freqs, h, grid))
    members = np.vstack(rows)
    # Subtract per-row mean so overall gain (mic calibration) drops out.
    members = members - members.mean(axis=1, keepdims=True)
    _TF_MEMBERS = members
    _TF_MEAN = members.mean(axis=0)
    _TF_STD = members.std(axis=0) + 1e-3
    _TF_SR = sr


def _tf_residual(vibration: np.ndarray, audio: np.ndarray, sr: int) -> dict[str, float]:
    _ensure_baseline(sr)
    grid = _tf_grid()
    freqs, h, cxy = dsp.transfer_function(vibration, audio, sr)
    logm = dsp.log_mag_on_grid(freqs, h, grid)
    logm = logm - float(np.mean(logm))
    assert _TF_MEAN is not None and _TF_STD is not None and _TF_MEMBERS is not None
    z = (logm - _TF_MEAN) / _TF_STD
    rmse_mean = float(np.sqrt(np.mean(z * z)))
    diffs = _TF_MEMBERS - logm[None, :]
    min_l2 = float(np.sqrt(np.mean(diffs * diffs, axis=1).min()))
    # Shape roughness: a physical TF is smooth on a log-f grid; noise is not.
    roughness = float(np.mean(np.diff(logm, n=2) ** 2))
    band_coh = dsp.band_mean(freqs, cxy, *dsp.COUPLING_BAND_HZ)
    return {
        "rmse_z": rmse_mean,
        "min_l2": min_l2,
        "roughness": roughness,
        "tf_coherence": band_coh,
    }


def _align(audio: np.ndarray, vibration: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray, float]:
    """Band-limit, estimate lag of audio vs vibration, shift audio backward."""
    lo, hi = dsp.COUPLING_BAND_HZ
    hi = min(hi, 0.45 * sr)
    a = dsp.bandpass(audio, sr, lo, hi)
    v = dsp.bandpass(vibration, sr, lo, hi)
    delay_s = dsp.gcc_phat_delay(v, a, sr)
    delay_samples = int(round(delay_s * sr))
    # Shift audio so it lines up with vibration (undo the lag).
    aligned_audio = dsp.shift_to_align(audio, -delay_samples)
    return aligned_audio, vibration, delay_s


def check_coherence(audio: np.ndarray, vibration: np.ndarray, sr: int) -> CheckResult:
    freqs, cxy = dsp.magnitude_squared_coherence(vibration, audio, sr)
    mean_couple = dsp.band_mean(freqs, cxy, *dsp.COUPLING_BAND_HZ)
    mean_speech = dsp.band_mean(freqs, cxy, *dsp.SPEECH_BAND_HZ)
    std_couple = dsp.band_std(freqs, cxy, *dsp.COUPLING_BAND_HZ)
    tv = dsp.time_varying_coherence(vibration, audio, sr)
    tv_mean = float(np.mean(tv))
    tv_std = float(np.std(tv)) if tv.size > 1 else 0.0
    # Authentic coupled speech: mean MSC typically well above 0.3 in-band
    # on these Welch settings; uncorrelated channels sit near 0.05–0.15.
    score = logistic_score(mean_couple, good=0.55, bad=0.12)
    # Penalize instability: large time variation of MSC.
    if tv_std > 0.18 and tv_mean < 0.45:
        score = min(score, logistic_score(tv_std, good=0.04, bad=0.28))
        code: str | None = COHERENCE_UNSTABLE if mean_couple >= 0.20 else COHERENCE_LOW
    elif mean_couple < 0.22:
        code = COHERENCE_LOW
        score = min(score, 0.35)
    else:
        code = None
    return CheckResult(
        name="coherence",
        score=clip01(score),
        reason_code=code,
        metrics={
            "msc_coupling_band": mean_couple,
            "msc_speech_band": mean_speech,
            "msc_std_coupling": std_couple,
            "msc_time_mean": tv_mean,
            "msc_time_std": tv_std,
        },
        note="Magnitude-squared coherence, 80–2000 Hz coupling band.",
    )


def check_transfer(audio: np.ndarray, vibration: np.ndarray, sr: int) -> CheckResult:
    m = _tf_residual(vibration, audio, sr)
    # rmse_z ~ 1 is typical of the bootstrap itself; shuffled pairs go much higher.
    score_z = logistic_score(m["rmse_z"], good=1.2, bad=4.5)
    score_l2 = logistic_score(m["min_l2"], good=0.8, bad=3.5)
    score_rough = logistic_score(m["roughness"], good=0.02, bad=0.35)
    score = clip01(0.5 * score_z + 0.3 * score_l2 + 0.2 * score_rough)
    code = TRANSFER_RESIDUAL_HIGH if (m["rmse_z"] > 3.0 or m["min_l2"] > 2.4) else None
    if code:
        score = min(score, 0.40)
    return CheckResult(
        name="transfer",
        score=score,
        reason_code=code,
        metrics=m,
        note=(
            "Vibration-to-air log|H(f)| residual vs a synthetic physically-"
            "plausible bootstrap (not a published human dataset)."
        ),
    )


def check_phase_latency(audio: np.ndarray, vibration: np.ndarray, sr: int) -> CheckResult:
    lo, hi = dsp.COUPLING_BAND_HZ
    hi = min(hi, 0.45 * sr)
    a = dsp.bandpass(audio, sr, lo, hi)
    v = dsp.bandpass(vibration, sr, lo, hi)
    delay_s = dsp.gcc_phat_delay(v, a, sr)
    delays = dsp.windowed_delays(v, a, sr)
    delay_std = float(np.std(delays)) if delays.size > 1 else 0.0
    dmin, dmax = dsp.PLAUSIBLE_DELAY_S
    in_window = dmin <= delay_s <= dmax
    delay_score = 1.0 if in_window else logistic_score(
        min(abs(delay_s - dmin), abs(delay_s - dmax)),
        good=0.0,
        bad=0.06,
    )
    # Drift: after removing the median delay, residual std should be small.
    drift_score = logistic_score(delay_std, good=0.002, bad=0.025)
    score = clip01(0.6 * delay_score + 0.4 * drift_score)
    code: str | None = None
    if not in_window:
        code = LATENCY_OUT_OF_BOUNDS
        score = min(score, 0.35)
    elif delay_std > 0.018:
        code = DRIFT_EXCESSIVE
        score = min(score, 0.45)
    return CheckResult(
        name="phase_latency",
        score=score,
        reason_code=code,
        metrics={
            "delay_s": delay_s,
            "delay_std_s": delay_std,
            "delay_median_s": float(np.median(delays)),
            "n_windows": float(delays.size),
        },
        note="GCC-PHAT latency and windowed drift (causality / bounded drift).",
    )


def check_decay(audio: np.ndarray, sr: int) -> CheckResult:
    off = dsp.offset_decay_stats(audio, sr)
    fits = dsp.decay_profiles(audio, sr)
    late = dsp.late_energy_ratio(audio, sr, split_s=0.08)
    if fits:
        taus = np.array([f.tau_s for f in fits], dtype=np.float64)
        r2s = np.array([f.r2 for f in fits], dtype=np.float64)
        median_tau = float(np.median(taus))
        max_tau = float(np.max(taus))
        mean_r2 = float(np.mean(r2s))
    else:
        median_tau = 0.0
        max_tau = 0.0
        mean_r2 = 0.0
    # Primary cue: how long the *offset* takes to fall from ~half-peak to silence.
    # Dry vocal-tract ringing + a short natural fade sits well below 100 ms.
    # Digital reverb stretches that offset to hundreds of milliseconds.
    offset_score = logistic_score(off["offset_s"], good=0.04, bad=0.28)
    tau_score = logistic_score(off["tau_s"] if off["tau_s"] > 0 else 0.01, good=0.02, bad=0.25)
    tail_score = logistic_score(off["tail_ratio"], good=0.15, bad=0.70)
    score = clip01(0.45 * offset_score + 0.35 * tau_score + 0.20 * tail_score)
    implausible = (
        off["offset_s"] > 0.16
        or off["tau_s"] > 0.14
        or (off["tail_ratio"] > 0.55 and off["offset_s"] > 0.10)
    )
    code = DECAY_IMPLAUSIBLE if implausible else None
    if code:
        score = min(score, 0.35)
    return CheckResult(
        name="decay",
        score=score,
        reason_code=code,
        metrics={
            "offset_s": off["offset_s"],
            "offset_tau_s": off["tau_s"],
            "offset_r2": off["r2"],
            "tail_ratio": off["tail_ratio"],
            "median_tau_s": median_tau,
            "max_tau_s": max_tau,
            "mean_r2": mean_r2,
            "late_energy_ratio": late,
            "n_fits": float(len(fits)),
        },
        note="Offset-tail exponential decay vs long digital-reverb tails.",
    )


def analyze_dual(audio: np.ndarray, vibration: np.ndarray, sr: int) -> list[CheckResult]:
    """Run the four dual-channel physical tests on already-mono signals."""
    audio = dsp.as_mono_float(audio)
    vibration = dsp.as_mono_float(vibration)
    n = min(audio.size, vibration.size)
    audio, vibration = audio[:n], vibration[:n]
    aligned, vib, _delay = _align(audio, vibration, sr)
    n2 = min(aligned.size, vib.size)
    aligned, vib = aligned[:n2], vib[:n2]
    return [
        check_coherence(aligned, vib, sr),
        check_transfer(aligned, vib, sr),
        check_phase_latency(audio, vibration, sr),  # latency on the *unshifted* pair
        check_decay(audio, sr),
    ]
