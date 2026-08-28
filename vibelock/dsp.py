"""Low-level DSP primitives for VibeLock.

Implements the signal-processing building blocks cited in
``docs/whitepaper.md``: magnitude-squared coherence, Hilbert phase,
LPC formant estimates, transfer-function estimation, GCC-PHAT delay,
and exponential decay envelopes.

This module is CPU-local (numpy + scipy only). It never performs
speech-to-text and never retains audio.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy import signal
from scipy.linalg import solve_toeplitz, toeplitz

# Speech-relevant band used throughout dual-channel tests
# (whitepaper: roughly 80–4000 Hz).
SPEECH_BAND_HZ: tuple[float, float] = (80.0, 4000.0)

# Overlap band where body-coupled vibration and air radiation
# are both expected to carry energy.
COUPLING_BAND_HZ: tuple[float, float] = (80.0, 2000.0)

# Anatomical delay window: tissue vibration and lip radiation of the
# same glottal event differ by vocal-tract group delay (a few ms), not
# tens of milliseconds. Implementation default, not a published ROC point.
PLAUSIBLE_DELAY_S: tuple[float, float] = (-0.008, 0.030)

# Closed-tube / formant ringing time constants are short.
# tau ≈ 1 / (pi * bandwidth); BW 50–300 Hz → ~1–6 ms.
# Digital reverb and synthetic ringing sit far above this.
PLAUSIBLE_DECAY_TAU_S: tuple[float, float] = (0.001, 0.080)


Array = NDArray[np.float64]


def as_mono_float(x: np.ndarray) -> Array:
    """Return a 1-D float64 vector. Stereo is averaged."""
    arr = np.asarray(x, dtype=np.float64)
    if arr.ndim == 2:
        arr = arr.mean(axis=1 if arr.shape[1] < arr.shape[0] else 0)
    arr = np.ravel(arr)
    if arr.size == 0:
        return arr
    peak = np.max(np.abs(arr))
    if peak > 8.0:
        # Integer PCM that wasn't scaled.
        arr = arr / max(peak, 1.0)
    return arr


def rms(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=np.float64)
    if x.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(x * x)))


def preemphasis(x: np.ndarray, coeff: float = 0.97) -> Array:
    x = np.asarray(x, dtype=np.float64)
    if x.size < 2:
        return x.copy()
    y = np.empty_like(x)
    y[0] = x[0]
    y[1:] = x[1:] - coeff * x[:-1]
    return y


def resample(x: np.ndarray, src_sr: int, dst_sr: int) -> Array:
    """Resample with polyphase filtering when rates differ."""
    x = as_mono_float(x)
    if src_sr == dst_sr or x.size == 0:
        return x
    g = np.gcd(int(src_sr), int(dst_sr))
    up, down = int(dst_sr) // g, int(src_sr) // g
    return np.asarray(signal.resample_poly(x, up, down), dtype=np.float64)


def bandpass(x: np.ndarray, sr: int, lo: float, hi: float, order: int = 4) -> Array:
    """Zero-phase Butterworth band-pass. Falls back to high/low-pass at edges."""
    x = as_mono_float(x)
    nyq = 0.5 * sr
    lo_n = max(lo / nyq, 1e-4)
    hi_n = min(hi / nyq, 0.999)
    if hi_n <= lo_n + 0.01:
        return x.copy()
    sos = signal.butter(order, [lo_n, hi_n], btype="band", output="sos")
    return np.asarray(signal.sosfiltfilt(sos, x), dtype=np.float64)


def frame_signal(
    x: np.ndarray,
    sr: int,
    frame_ms: float = 25.0,
    hop_ms: float = 10.0,
    window: str = "hann",
) -> tuple[Array, int, int]:
    """Return overlapping frames (n_frames, n_win), window length, hop."""
    x = as_mono_float(x)
    n_win = max(8, int(round(frame_ms * 0.001 * sr)))
    hop = max(1, int(round(hop_ms * 0.001 * sr)))
    if x.size < n_win:
        pad = np.zeros(n_win, dtype=np.float64)
        pad[: x.size] = x
        frames = pad[np.newaxis, :]
        if window:
            frames = frames * signal.get_window(window, n_win, fftbins=True)
        return frames, n_win, hop
    n_frames = 1 + (x.size - n_win) // hop
    idx = np.arange(n_win)[None, :] + hop * np.arange(n_frames)[:, None]
    frames = x[idx]
    if window:
        frames = frames * signal.get_window(window, n_win, fftbins=True)
    return frames, n_win, hop


def next_pow2(n: int) -> int:
    n = max(int(n), 1)
    return 1 << (n - 1).bit_length()


def welch_nperseg(n: int, sr: int) -> int:
    """Choose a Welch segment length that still yields several averages."""
    target = int(round(0.032 * sr))  # ~32 ms
    nper = max(64, next_pow2(target))
    nper = min(nper, max(64, n // 4))
    return int(max(64, nper))


def magnitude_squared_coherence(
    x: np.ndarray,
    y: np.ndarray,
    sr: int,
    nperseg: int | None = None,
) -> tuple[Array, Array]:
    """Welch magnitude-squared coherence C_xy(f) in [0, 1].

    Whitepaper: vibration–audio coherence in speech-relevant bands.
    Authentic coupled sources produce stable high coherence where both
    channels have energy; independent or vocoded substitutes do not.
    """
    x = as_mono_float(x)
    y = as_mono_float(y)
    n = min(x.size, y.size)
    x, y = x[:n], y[:n]
    if n < 128:
        freqs = np.fft.rfftfreq(256, 1.0 / sr)
        return freqs, np.zeros_like(freqs)
    nper = nperseg or welch_nperseg(n, sr)
    nper = min(nper, n // 2)
    with np.errstate(invalid="ignore", divide="ignore"):
        freqs, cxy = signal.coherence(x, y, fs=sr, nperseg=nper, noverlap=nper // 2)
    cxy = np.nan_to_num(np.asarray(cxy, dtype=np.float64), nan=0.0, posinf=0.0, neginf=0.0)
    return np.asarray(freqs, dtype=np.float64), cxy


def band_mean(freqs: np.ndarray, values: np.ndarray, lo: float, hi: float) -> float:
    mask = (freqs >= lo) & (freqs <= hi)
    if not np.any(mask):
        return 0.0
    v = values[mask]
    v = v[np.isfinite(v)]
    if v.size == 0:
        return 0.0
    return float(np.mean(v))


def band_std(freqs: np.ndarray, values: np.ndarray, lo: float, hi: float) -> float:
    mask = (freqs >= lo) & (freqs <= hi)
    if not np.any(mask):
        return 0.0
    v = values[mask]
    v = v[np.isfinite(v)]
    if v.size < 2:
        return 0.0
    return float(np.std(v))


def time_varying_coherence(
    x: np.ndarray,
    y: np.ndarray,
    sr: int,
    win_s: float = 0.25,
    hop_s: float = 0.10,
    lo: float = COUPLING_BAND_HZ[0],
    hi: float = COUPLING_BAND_HZ[1],
) -> Array:
    """Mean in-band MSC for successive windows (coherence stability)."""
    x = as_mono_float(x)
    y = as_mono_float(y)
    n = min(x.size, y.size)
    win = max(256, int(round(win_s * sr)))
    hop = max(64, int(round(hop_s * sr)))
    vals: list[float] = []
    start = 0
    while start + win <= n:
        f, c = magnitude_squared_coherence(x[start : start + win], y[start : start + win], sr)
        vals.append(band_mean(f, c, lo, hi))
        start += hop
    if not vals:
        f, c = magnitude_squared_coherence(x[:n], y[:n], sr)
        return np.array([band_mean(f, c, lo, hi)], dtype=np.float64)
    return np.asarray(vals, dtype=np.float64)


def hilbert_envelope(x: np.ndarray) -> Array:
    x = as_mono_float(x)
    if x.size < 8:
        return np.abs(x)
    return np.abs(signal.hilbert(x)).astype(np.float64)


def instantaneous_phase(x: np.ndarray) -> Array:
    """Unwrapped instantaneous phase via the analytic signal (Hilbert)."""
    x = as_mono_float(x)
    if x.size < 8:
        return np.zeros_like(x)
    return np.unwrap(np.angle(signal.hilbert(x))).astype(np.float64)


def instantaneous_frequency(x: np.ndarray, sr: int) -> Array:
    phase = instantaneous_phase(x)
    if phase.size < 2:
        return np.zeros(max(phase.size, 0), dtype=np.float64)
    return np.diff(phase) * (sr / (2.0 * np.pi))


def phase_jump_rate(x: np.ndarray, sr: int, jump_rad: float = 2.2) -> float:
    """Fraction of samples whose wrapped phase step exceeds ``jump_rad``.

    Natural voiced speech has large phase steps at glottal instants, but
    those are sparse and quasi-periodic. Dense irregular jumps indicate
    splices, codec resets, or randomized phase.
    """
    x = as_mono_float(x)
    if x.size < 32:
        return 0.0
    analytic = signal.hilbert(bandpass(x, sr, 80.0, min(4000.0, sr * 0.45)))
    wrapped = np.angle(analytic)
    step = np.diff(wrapped)
    step = (step + np.pi) % (2 * np.pi) - np.pi
    n_jumps = int(np.count_nonzero(np.abs(step) > jump_rad))
    duration = step.size / float(sr)
    # Jumps per second (a 1-sample wrap every 8 ms is ~125 Hz of jumps,
    # not a 0.008 fraction of samples).
    return float(n_jumps / max(duration, 1e-9))


def phase_residual_variance(x: np.ndarray, sr: int) -> float:
    """Variance of instantaneous frequency after subtracting a slow trend.

    Overly-flat phase (some vocoders / zero-phase reconstructions) yields
    an unnaturally small residual. Chaotic phase yields a huge residual.
    """
    x = as_mono_float(x)
    if x.size < 64:
        return 0.0
    xb = bandpass(x, sr, 80.0, min(1200.0, sr * 0.45))
    inst = instantaneous_frequency(xb, sr)
    inst = inst[np.isfinite(inst)]
    if inst.size < 32:
        return 0.0
    # Keep voiced-ish region: 60–400 Hz instantaneous freq.
    voiced = inst[(inst > 50.0) & (inst < 500.0)]
    work = voiced if voiced.size > 16 else inst
    # Detrend with a moving median (~40 ms).
    k = max(5, int(round(0.04 * sr)) | 1)
    k = min(k, work.size | 1)
    if k < 5:
        return float(np.var(work))
    pad = k // 2
    padded = np.pad(work, pad, mode="edge")
    trend = np.lib.stride_tricks.sliding_window_view(padded, k).mean(axis=1)[: work.size]
    residual = work - trend
    return float(np.var(residual))


def gcc_phat_delay(x: np.ndarray, y: np.ndarray, sr: int, max_lag_s: float = 0.08) -> float:
    """Estimate delay of ``y`` relative to ``x`` in seconds (GCC-PHAT).

    Positive → ``y`` lags ``x`` (air lags vibration).
    """
    x = as_mono_float(x)
    y = as_mono_float(y)
    n = min(x.size, y.size)
    x, y = x[:n], y[:n]
    if n < 32:
        return 0.0
    nfft = next_pow2(2 * n)
    X = np.fft.rfft(x, n=nfft)
    Y = np.fft.rfft(y, n=nfft)
    # IFFT(Y * conj(X)): positive lag => y lags x.
    r = Y * np.conj(X)
    r = r / (np.abs(r) + 1e-12)
    cc = np.fft.irfft(r, n=nfft)
    max_lag = min(n - 1, int(round(max_lag_s * sr)))
    # cc[k] = lag +k of y vs x for k small; negative lags at the end.
    pos = cc[: max_lag + 1]
    neg = cc[-max_lag:] if max_lag > 0 else np.array([], dtype=cc.dtype)
    lags = np.concatenate([np.arange(-max_lag, 0), np.arange(0, max_lag + 1)])
    vals = np.concatenate([neg, pos])
    peak = int(np.argmax(np.abs(vals)))
    return float(lags[peak]) / float(sr)


def windowed_delays(
    x: np.ndarray,
    y: np.ndarray,
    sr: int,
    win_s: float = 0.30,
    hop_s: float = 0.10,
) -> Array:
    """Per-window GCC-PHAT delays for drift / causality checks."""
    x = as_mono_float(x)
    y = as_mono_float(y)
    n = min(x.size, y.size)
    win = max(256, int(round(win_s * sr)))
    hop = max(64, int(round(hop_s * sr)))
    out: list[float] = []
    start = 0
    while start + win <= n:
        out.append(gcc_phat_delay(x[start : start + win], y[start : start + win], sr))
        start += hop
    if not out:
        out.append(gcc_phat_delay(x[:n], y[:n], sr))
    return np.asarray(out, dtype=np.float64)


def shift_to_align(x: np.ndarray, delay_samples: int) -> Array:
    """Shift ``x`` by ``delay_samples`` (positive = to the right) with zero fill."""
    x = as_mono_float(x)
    d = int(delay_samples)
    if d == 0:
        return x.copy()
    out = np.zeros_like(x)
    if d > 0:
        if d < x.size:
            out[d:] = x[: x.size - d]
    else:
        d = -d
        if d < x.size:
            out[: x.size - d] = x[d:]
    return out


def transfer_function(
    x: np.ndarray,
    y: np.ndarray,
    sr: int,
    nperseg: int | None = None,
) -> tuple[Array, Array, Array]:
    """Welch estimate of H(f) = P_xy(f) / P_xx(f).

    ``x`` is the input (vibration), ``y`` the output (air).
    Returns ``(freqs, H_complex, Cxy)``.
    """
    x = as_mono_float(x)
    y = as_mono_float(y)
    n = min(x.size, y.size)
    x, y = x[:n], y[:n]
    if n < 128:
        freqs = np.fft.rfftfreq(256, 1.0 / sr)
        z = np.zeros_like(freqs, dtype=np.complex128)
        return freqs, z, np.zeros_like(freqs)
    nper = nperseg or welch_nperseg(n, sr)
    nper = min(nper, n // 2)
    freqs, pxx = signal.welch(x, fs=sr, nperseg=nper, noverlap=nper // 2)
    _, pxy = signal.csd(x, y, fs=sr, nperseg=nper, noverlap=nper // 2)
    with np.errstate(invalid="ignore", divide="ignore"):
        _, cxy = signal.coherence(x, y, fs=sr, nperseg=nper, noverlap=nper // 2)
    cxy = np.nan_to_num(np.asarray(cxy, dtype=np.float64), nan=0.0, posinf=0.0, neginf=0.0)
    h = pxy / (pxx + 1e-20)
    return (
        np.asarray(freqs, dtype=np.float64),
        np.asarray(h, dtype=np.complex128),
        np.asarray(cxy, dtype=np.float64),
    )


def log_mag_on_grid(
    freqs: np.ndarray,
    h: np.ndarray,
    grid: np.ndarray,
) -> Array:
    """Interpolate log-magnitude of H onto a common frequency grid."""
    mag = np.abs(np.asarray(h))
    mag = np.maximum(mag, 1e-12)
    logm = np.log(mag)
    logm = np.nan_to_num(logm, nan=-30.0, posinf=10.0, neginf=-30.0)
    # scipy welch freqs are linear; grid may be log-spaced.
    out = np.interp(grid, freqs, logm, left=logm[0], right=logm[-1])
    return np.asarray(out, dtype=np.float64)


def spectral_smoothness(x: np.ndarray, sr: int) -> dict[str, float]:
    """Fine-structure energy of the log-magnitude spectrum.

    Too-low values: vocoder / heavily smoothed synthetic spectra.
    Too-high values: noise-like or metallic comb artifacts.
    """
    frames, n_win, _ = frame_signal(x, sr, frame_ms=30.0, hop_ms=10.0)
    if frames.size == 0:
        return {"fine_var": 0.0, "centroid_std": 0.0}
    nfft = next_pow2(n_win)
    spec = np.abs(np.fft.rfft(frames, n=nfft)) + 1e-12
    logspec = np.log(spec)
    # Subtract a 5-bin moving average envelope (formant-scale).
    k = 5
    kernel = np.ones(k) / k
    smooth = np.apply_along_axis(lambda row: np.convolve(row, kernel, mode="same"), 1, logspec)
    fine = logspec - smooth
    fine_var = float(np.mean(np.var(fine, axis=1)))
    freqs = np.fft.rfftfreq(nfft, 1.0 / sr)
    mag = spec
    centroid = np.sum(freqs[None, :] * mag, axis=1) / np.sum(mag, axis=1)
    return {"fine_var": fine_var, "centroid_std": float(np.std(centroid))}


def spectral_flux(x: np.ndarray, sr: int) -> Array:
    frames, n_win, _ = frame_signal(x, sr, frame_ms=25.0, hop_ms=10.0)
    nfft = next_pow2(n_win)
    mag = np.abs(np.fft.rfft(frames, n=nfft))
    mag = mag / (np.linalg.norm(mag, axis=1, keepdims=True) + 1e-12)
    if mag.shape[0] < 2:
        return np.zeros(1, dtype=np.float64)
    diff = np.diff(mag, axis=0)
    flux = np.sqrt(np.sum(diff * diff, axis=1))
    return flux.astype(np.float64)


def rms_envelope(x: np.ndarray, sr: int, hop_ms: float = 10.0) -> Array:
    frames, _, _ = frame_signal(x, sr, frame_ms=25.0, hop_ms=hop_ms, window="hann")
    return np.sqrt(np.mean(frames * frames, axis=1) + 1e-18)


def lpc_coefficients(x: np.ndarray, order: int) -> Array:
    """Autocorrelation LPC via Levinson–Durbin (Toeplitz solve).

    Used as a formant-ish peak tracker, not as a codec.
    """
    x = as_mono_float(x)
    if x.size <= order + 2:
        return np.zeros(order, dtype=np.float64)
    x = x - np.mean(x)
    peak = np.max(np.abs(x))
    if peak < 1e-12:
        return np.zeros(order, dtype=np.float64)
    x = x / peak
    r = np.correlate(x, x, mode="full")[x.size - 1 : x.size + order]
    r = np.asarray(r, dtype=np.float64)
    r[0] = r[0] * 1.0001 + 1e-10
    try:
        a = solve_toeplitz(r[:-1], -r[1:])
    except np.linalg.LinAlgError:
        matrix = toeplitz(r[:-1])
        a, *_ = np.linalg.lstsq(matrix, -r[1:], rcond=None)
    return np.asarray(a, dtype=np.float64)


def formants_from_lpc(
    a: np.ndarray,
    sr: int,
    n_formants: int = 3,
) -> tuple[Array, Array]:
    """Positive-frequency LPC roots → (frequencies_hz, bandwidths_hz)."""
    a = np.asarray(a, dtype=np.float64)
    if a.size == 0 or not np.all(np.isfinite(a)):
        return np.zeros(0), np.zeros(0)
    poly = np.concatenate(([1.0], a))
    roots = np.roots(poly)
    roots = roots[np.imag(roots) >= 0.0]
    if roots.size == 0:
        return np.zeros(0), np.zeros(0)
    ang = np.angle(roots)
    freqs = ang * sr / (2.0 * np.pi)
    radii = np.abs(roots)
    bw = -np.log(np.clip(radii, 1e-8, 0.999999)) * sr / np.pi
    ok = (
        (freqs > 90.0)
        & (freqs < min(4000.0, 0.45 * sr))
        & (bw < 1200.0)
        & (radii > 0.55)
    )
    freqs, bw = freqs[ok], bw[ok]
    order = np.argsort(freqs)
    freqs, bw = freqs[order], bw[order]
    return freqs[:n_formants], bw[:n_formants]


def formant_tracks(
    x: np.ndarray,
    sr: int,
    order: int | None = None,
    n_formants: int = 3,
    frame_ms: float = 25.0,
    hop_ms: float = 10.0,
) -> Array:
    """LPC formant tracks. Shape (n_frames, n_formants); NaN where missing."""
    x = as_mono_float(x)
    xp = preemphasis(x)
    frames, n_win, _ = frame_signal(xp, sr, frame_ms=frame_ms, hop_ms=hop_ms)
    if order is None:
        order = max(8, int(round(sr / 1000)) + 2)
        order = min(order, n_win - 2)
    rms_f = np.sqrt(np.mean(frames * frames, axis=1) + 1e-18)
    thresh = 0.15 * (np.percentile(rms_f, 80) + 1e-12)
    tracks = np.full((frames.shape[0], n_formants), np.nan, dtype=np.float64)
    for i, fr in enumerate(frames):
        if rms_f[i] < thresh:
            continue
        a = lpc_coefficients(fr, order)
        freqs, _bw = formants_from_lpc(a, sr, n_formants=n_formants)
        n = min(n_formants, freqs.size)
        tracks[i, :n] = freqs[:n]
    return tracks


def formant_stability(tracks: np.ndarray) -> dict[str, float]:
    """Frame-to-frame formant jump statistics (Hz)."""
    if tracks.size == 0:
        return {"median_jump_hz": 0.0, "p95_jump_hz": 0.0, "voiced_frac": 0.0}
    jumps: list[float] = []
    voiced = 0
    for col in range(tracks.shape[1]):
        series = tracks[:, col]
        for a, b in zip(series[:-1], series[1:]):
            if np.isfinite(a) and np.isfinite(b):
                jumps.append(abs(float(b - a)))
                voiced += 1
    voiced_frac = float(np.mean(np.any(np.isfinite(tracks), axis=1))) if tracks.ndim == 2 else 0.0
    if not jumps:
        return {"median_jump_hz": 0.0, "p95_jump_hz": 0.0, "voiced_frac": voiced_frac}
    arr = np.asarray(jumps, dtype=np.float64)
    return {
        "median_jump_hz": float(np.median(arr)),
        "p95_jump_hz": float(np.percentile(arr, 95)),
        "voiced_frac": voiced_frac,
    }


@dataclass
class DecayFit:
    tau_s: float
    r2: float
    peak_index: int
    n_points: int


def _fit_exponential(env: np.ndarray, sr: int) -> tuple[float, float]:
    """Least-squares log-envelope fit. Returns (tau_seconds, r2)."""
    env = np.asarray(env, dtype=np.float64)
    env = np.maximum(env, 1e-12)
    if env.size < 8:
        return 0.0, 0.0
    # Require a decaying shape.
    if env[-1] >= env[0] * 0.98:
        return 0.0, 0.0
    t = np.arange(env.size, dtype=np.float64) / float(sr)
    y = np.log(env)
    # Drop samples that have already hit the noise floor.
    floor = np.log(max(np.max(env) * 0.02, 1e-8))
    mask = y > floor
    if np.count_nonzero(mask) < 8:
        return 0.0, 0.0
    t, y = t[mask], y[mask]
    A = np.vstack([t, np.ones_like(t)]).T
    coeff, *_ = np.linalg.lstsq(A, y, rcond=None)
    slope, intercept = float(coeff[0]), float(coeff[1])
    yhat = slope * t + intercept
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2) + 1e-18)
    r2 = 1.0 - ss_res / ss_tot
    if slope >= -1e-6:
        return 0.0, max(r2, 0.0)
    tau = -1.0 / slope
    return float(tau), float(max(min(r2, 1.0), 0.0))


def decay_profiles(
    x: np.ndarray,
    sr: int,
    n_peaks: int = 8,
    tail_ms: float = 60.0,
) -> list[DecayFit]:
    """Fit exponential decays after Hilbert-envelope peaks.

    Whitepaper: authentic vocal-tract ringing is short and roughly
    exponential. Digital reverb and synthetic ringing produce long or
    poorly exponential tails.
    """
    x = as_mono_float(x)
    if x.size < int(0.05 * sr):
        return []
    env = hilbert_envelope(bandpass(x, sr, 80.0, min(4000.0, sr * 0.45)))
    # Light smoothing so we pick syllable / pulse groups, not every glottal peak.
    win = max(5, int(round(0.008 * sr)) | 1)
    env_s = signal.fftconvolve(env, np.ones(win) / win, mode="same")
    distance = max(int(0.04 * sr), 1)
    peaks, _props = signal.find_peaks(env_s, distance=distance)
    if peaks.size == 0:
        return []
    # Prefer high peaks that still have a tail inside the signal.
    tail = int(round(tail_ms * 0.001 * sr))
    scores = env_s[peaks]
    order = np.argsort(scores)[::-1]
    fits: list[DecayFit] = []
    for idx in peaks[order]:
        if len(fits) >= n_peaks:
            break
        end = idx + tail
        if end >= env.size:
            continue
        # Start a few samples after the peak so the attack is excluded.
        start = min(idx + max(2, int(0.002 * sr)), end - 8)
        tau, r2 = _fit_exponential(env[start:end], sr)
        if tau <= 0.0:
            continue
        fits.append(DecayFit(tau_s=tau, r2=r2, peak_index=int(idx), n_points=end - start))
    return fits


def offset_decay_stats(x: np.ndarray, sr: int) -> dict[str, float]:
    """Characterize the utterance *offset* tail, not mid-voicing ripple.

    Do not treat a long low-level reverb tail as 'silence to skip' — that
    is the signal. Measure how long the envelope takes to fall from half
    peak to 5% peak, and how much energy lives after the half-peak point.
    """
    x = as_mono_float(x)
    if x.size < 16:
        return {"offset_s": 0.0, "tau_s": 0.0, "r2": 0.0, "tail_ratio": 0.0}
    env = hilbert_envelope(bandpass(x, sr, 80.0, min(4000.0, sr * 0.45)))
    win = max(5, int(round(0.012 * sr)) | 1)
    env_s = signal.fftconvolve(env, np.ones(win) / win, mode="same")
    peak = float(np.max(env_s) + 1e-12)
    above = np.where(env_s >= 0.50 * peak)[0]
    if above.size == 0:
        return {"offset_s": 0.0, "tau_s": 0.0, "r2": 0.0, "tail_ratio": 0.0}
    last_half = int(above[-1])
    rest = env_s[last_half:]
    floor_idx = np.where(rest <= 0.05 * peak)[0]
    if floor_idx.size:
        decay_end = last_half + int(floor_idx[0])
    else:
        decay_end = int(env_s.size - 1)
    offset_s = max(0.0, (decay_end - last_half) / float(sr))
    tau, r2 = _fit_exponential(env[last_half : max(decay_end, last_half + 8) + 1], sr)
    after = float(np.sum(env[last_half:] ** 2) + 1e-18)
    pre_n = int(round(0.08 * sr))
    pre_start = max(0, last_half - pre_n)
    before = float(np.sum(env[pre_start:last_half] ** 2) + 1e-18)
    tail_ratio = after / (after + before)
    return {
        "offset_s": float(offset_s),
        "tau_s": float(tau),
        "r2": float(r2),
        "tail_ratio": float(tail_ratio),
    }


def late_energy_ratio(x: np.ndarray, sr: int, split_s: float = 0.08) -> float:
    """Energy after ``split_s`` following the global envelope peak.

    Long synthetic reverb parks energy far after anatomical ringing dies.
    """
    x = as_mono_float(x)
    env = hilbert_envelope(x)
    if env.size == 0:
        return 0.0
    peak = int(np.argmax(env))
    split = peak + int(round(split_s * sr))
    if split >= env.size - 4:
        return 0.0
    early = float(np.sum(env[peak:split] ** 2) + 1e-18)
    late = float(np.sum(env[split:] ** 2))
    return late / (early + late)


def modulation_spectrum_peak(
    x: np.ndarray,
    sr: int,
    lo_hz: float = 40.0,
    hi_hz: float = 250.0,
) -> dict[str, float]:
    """Peak of the Hilbert-envelope modulation spectrum in ``lo–hi`` Hz.

    Vocoder / vocoder-hop buzz often concentrates envelope energy at a
    fixed frame rate (commonly 50–200 Hz).
    """
    x = as_mono_float(x)
    env = hilbert_envelope(x)
    env = env - np.mean(env)
    if env.size < 64:
        return {"peak_hz": 0.0, "peak_to_med": 0.0}
    nfft = next_pow2(env.size)
    spec = np.abs(np.fft.rfft(env, n=nfft))
    freqs = np.fft.rfftfreq(nfft, 1.0 / sr)
    mask = (freqs >= lo_hz) & (freqs <= hi_hz)
    if not np.any(mask):
        return {"peak_hz": 0.0, "peak_to_med": 0.0}
    band = spec[mask]
    bf = freqs[mask]
    k = int(np.argmax(band))
    med = float(np.median(band) + 1e-12)
    return {"peak_hz": float(bf[k]), "peak_to_med": float(band[k] / med)}


def estimate_f0(x: np.ndarray, sr: int, lo: float = 70.0, hi: float = 350.0) -> float:
    """Autocorrelation F0 estimate (Hz). 0 if unvoiced / too short."""
    x = as_mono_float(x)
    if x.size < int(0.04 * sr):
        return 0.0
    # Use a mid-signal window so fades do not dominate.
    n = min(x.size, int(0.08 * sr))
    start = max(0, (x.size - n) // 2)
    seg = x[start : start + n]
    seg = seg - np.mean(seg)
    if np.max(np.abs(seg)) < 1e-12:
        return 0.0
    corr = np.correlate(seg, seg, mode="full")[n - 1 :]
    min_lag = max(1, int(round(sr / hi)))
    max_lag = min(corr.size - 1, int(round(sr / lo)))
    if max_lag <= min_lag + 1:
        return 0.0
    lag = min_lag + int(np.argmax(corr[min_lag : max_lag + 1]))
    return float(sr / lag) if lag > 0 else 0.0
