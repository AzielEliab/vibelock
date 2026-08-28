"""Synthetic attacks used by tests. No hardware, no recorded speech."""

from __future__ import annotations

import numpy as np
from scipy import signal

from vibelock.synth import DualPair, make_pair, vocal_tract, glottal_source

SR = 16000


def uncorrelated_pair(sr: int = SR) -> DualPair:
    a = make_pair(duration_s=1.2, sr=sr, f0=110.0, seed=11)
    b = make_pair(duration_s=1.2, sr=sr, f0=190.0, seed=99)
    n = min(a.audio.size, b.vibration.size)
    return DualPair(
        audio=a.audio[:n],
        vibration=b.vibration[:n],
        sr=sr,
        f0=0.0,
        formants=a.formants,
    )


def delayed_pair(pair: DualPair, delay_s: float = 0.08) -> DualPair:
    n = int(round(delay_s * pair.sr))
    audio = np.concatenate([np.zeros(n), pair.audio])
    vib = np.concatenate([pair.vibration, np.zeros(n)])
    return DualPair(audio=audio, vibration=vib, sr=pair.sr, f0=pair.f0, formants=pair.formants)


def long_reverb(x: np.ndarray, sr: int, tau_s: float = 0.28) -> np.ndarray:
    """Feedback comb — digital metallic ringing, not a 17 cm tube.

    ``tau_s`` is mapped to a long decay: feedback is chosen so the envelope
    drops ~20 dB over roughly ``tau_s`` seconds. Zero-mean speech through a
    one-pole exponential IR does not leave a loud tail; a comb does.
    """
    x = np.asarray(x, dtype=np.float64)
    delay = max(8, int(round(0.037 * sr)))
    # 20 dB down in tau_s: 0.1 = fb ** (tau_s / delay_s)
    delay_s = delay / float(sr)
    fb = float(np.clip(0.1 ** (delay_s / max(tau_s, 1e-3)), 0.80, 0.97))
    pad = np.concatenate([x, np.zeros(int(round(1.4 * sr)), dtype=np.float64)])
    a = np.zeros(delay + 1, dtype=np.float64)
    a[0] = 1.0
    a[delay] = -fb
    wet = signal.lfilter([1.0], a, pad)
    peak = np.max(np.abs(wet)) + 1e-12
    return (wet / peak).astype(np.float64)


def phase_scrambled(x: np.ndarray, sr: int, seed: int = 3) -> np.ndarray:
    """Insert irregular pi phase jumps (hard sign flips on short hops)."""
    rng = np.random.default_rng(seed)
    y = np.array(x, dtype=np.float64, copy=True)
    hop = max(8, int(round(0.006 * sr)))
    for i in range(0, y.size, hop):
        if rng.random() < 0.65:
            y[i : i + hop] *= -1.0
    peak = np.max(np.abs(y)) + 1e-12
    return y / peak


def zero_phase(x: np.ndarray, sr: int) -> np.ndarray:
    nper = 512
    _f, _t, zxx = signal.stft(x, fs=sr, nperseg=nper, noverlap=nper // 2)
    _, y = signal.istft(np.abs(zxx), fs=sr, nperseg=nper, noverlap=nper // 2)
    n = min(x.size, y.size)
    out = np.zeros_like(x, dtype=np.float64)
    out[:n] = np.real(y[:n])
    peak = np.max(np.abs(out)) + 1e-12
    return out / peak


def hard_splice(sr: int = SR) -> np.ndarray:
    left = make_pair(duration_s=0.7, sr=sr, f0=105.0, seed=2).audio
    right = make_pair(
        duration_s=0.7,
        sr=sr,
        f0=210.0,
        formants=((750.0, 90.0), (1900.0, 120.0), (2900.0, 160.0)),
        seed=8,
    ).audio
    right = 0.35 * right
    click = np.zeros(int(0.004 * sr))
    click[0] = 0.95
    y = np.concatenate([left, click, right])
    peak = np.max(np.abs(y)) + 1e-12
    return (y / peak).astype(np.float64)


def unstable_formants(sr: int = SR, duration_s: float = 1.2, seed: int = 5) -> np.ndarray:
    rng = np.random.default_rng(seed)
    hop = int(0.025 * sr)
    n = int(duration_s * sr)
    chunks: list[np.ndarray] = []
    pos = 0
    while pos < n:
        f0 = float(rng.uniform(90.0, 240.0))
        f1 = float(rng.uniform(300.0, 900.0))
        f2 = float(rng.uniform(1100.0, 2200.0))
        f3 = float(rng.uniform(2400.0, 3400.0))
        src = glottal_source(hop + 64, sr, f0=f0, rng=rng)
        chunk = vocal_tract(src, sr, ((f1, 80.0), (f2, 110.0), (f3, 150.0)))
        chunks.append(chunk[:hop])
        pos += hop
    y = np.concatenate(chunks)[:n]
    peak = np.max(np.abs(y)) + 1e-12
    return (y / peak).astype(np.float64)


def vocoder_buzz(x: np.ndarray, sr: int, hop_hz: float = 100.0) -> np.ndarray:
    t = np.arange(x.size, dtype=np.float64) / float(sr)
    gain = 0.25 + 0.75 * (np.mod(t * hop_hz, 1.0) < 0.55).astype(np.float64)
    y = x * gain
    peak = np.max(np.abs(y)) + 1e-12
    return (y / peak).astype(np.float64)
