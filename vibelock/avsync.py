"""Audio–visual physical coupling (talking-head sync).

A real mouth radiates the same events the microphone hears. Deepfake
talking heads often paint a face that is late, early, or independent
of the waveform. VibeLock compares the audio RMS envelope to visual
motion energy (center crop) and to a GCC-PHAT delay between those
envelopes.

This is not lip-reading and not identity.
"""

from __future__ import annotations

import numpy as np

from vibelock import dsp
from vibelock.media import frames_to_rgb01
from vibelock.scoring import AV_SYNC_FAIL, CheckResult, clip01, logistic_score
from vibelock.temporal import motion_energy


def audio_envelope(audio: np.ndarray, sr: int, n_frames: int) -> np.ndarray:
    """RMS envelope resampled to ``n_frames`` visual hops."""
    x = dsp.as_mono_float(audio)
    if x.size < 8 or n_frames < 2:
        return np.zeros(max(n_frames, 1), dtype=np.float64)
    hop = max(1, x.size // n_frames)
    env = []
    for i in range(n_frames):
        sl = x[i * hop : min(x.size, (i + 1) * hop + hop // 2)]
        env.append(dsp.rms(sl) if sl.size else 0.0)
    arr = np.asarray(env, dtype=np.float64)
    arr = arr - np.mean(arr)
    peak = float(np.max(np.abs(arr)) + 1e-12)
    return arr / peak


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    n = min(a.size, b.size)
    if n < 4:
        return 0.0
    a = a[:n] - np.mean(a[:n])
    b = b[:n] - np.mean(b[:n])
    den = float(np.linalg.norm(a) * np.linalg.norm(b)) + 1e-12
    return float(np.dot(a, b) / den)


def check_av_sync(
    audio: np.ndarray,
    sr: int,
    frames: np.ndarray,
    fps: float = 25.0,
) -> CheckResult:
    stack = frames_to_rgb01(frames)
    if stack.shape[0] < 4:
        return CheckResult("av_sync", 0.5, None, {}, "Need at least 4 frames for A/V sync.")
    motion = motion_energy(stack)
    # motion_energy is length T-1; pad to T with an edge sample.
    motion_t = np.concatenate([motion[:1], motion])
    env = audio_envelope(audio, sr, int(stack.shape[0]))
    n = min(env.size, motion_t.size)
    env, motion_t = env[:n], motion_t[:n]
    # Normalize motion the same way.
    m = motion_t - np.mean(motion_t)
    peak = float(np.max(np.abs(m)) + 1e-12)
    m = m / peak
    corr = _corr(env, m)
    # GCC-PHAT-ish delay on the two envelopes (sample = one frame).
    delay_frames = 0.0
    if n >= 8:
        nfft = dsp.next_pow2(2 * n)
        X = np.fft.rfft(env, n=nfft)
        Y = np.fft.rfft(m, n=nfft)
        r = Y * np.conj(X)
        r = r / (np.abs(r) + 1e-12)
        cc = np.fft.irfft(r, n=nfft)
        max_lag = min(n // 3, 8)
        pos = cc[: max_lag + 1]
        neg = cc[-max_lag:] if max_lag else np.array([], dtype=cc.dtype)
        lags = np.concatenate([np.arange(-max_lag, 0), np.arange(0, max_lag + 1)])
        vals = np.concatenate([neg, pos])
        delay_frames = float(lags[int(np.argmax(np.abs(vals)))])
    delay_s = delay_frames / float(max(fps, 1e-6))
    # Talking heads: |delay| under ~80 ms is causal lip sync; 200 ms+ is dubbed.
    delay_score = logistic_score(abs(delay_s), good=0.04, bad=0.22)
    corr_score = logistic_score(corr, good=0.55, bad=0.05)
    # Anti-correlated motion (mouth moving in silence) is worse than zero.
    if corr < 0:
        corr_score = min(corr_score, 0.25)
    score = clip01(0.65 * corr_score + 0.35 * delay_score)
    code = None
    if corr < 0.12 or abs(delay_s) > 0.16:
        code = AV_SYNC_FAIL
        score = min(score, 0.22)
    return CheckResult(
        name="av_sync",
        score=score,
        reason_code=code,
        metrics={
            "av_corr": float(corr),
            "delay_s": float(delay_s),
            "delay_frames": float(delay_frames),
            "fps": float(fps),
        },
        note="Audio RMS vs center-motion energy (talking-head coupling).",
    )


def analyze_av(
    audio: np.ndarray,
    sr: int,
    frames: np.ndarray,
    fps: float = 25.0,
) -> list[CheckResult]:
    return [check_av_sync(audio, sr, frames, fps=fps)]
