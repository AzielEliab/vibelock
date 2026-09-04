"""Synthetic images, clips, and A/V pairs for the deepfake engine.

These generators are physics-inspired cartoons, not a published corpus.
Authentic stills are 1/f scenes under one illuminant plus sensor noise.
Attacks add generator upsampling, noise mismatch, blend seams, flicker,
and audio that does not drive the mouth.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy import ndimage

from vibelock.synth import make_pair

Array = NDArray[np.float64]


def _rng(seed: int | None) -> np.random.Generator:
    return np.random.default_rng(seed)


def _one_over_f(h: int, w: int, rng: np.random.Generator, beta: float = 1.25) -> Array:
    spec = rng.normal(0.0, 1.0, (h, w)) + 1j * rng.normal(0.0, 1.0, (h, w))
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    ramp = np.sqrt(fx * fx + fy * fy)
    ramp[0, 0] = 1.0
    field = np.real(np.fft.ifft2(spec / (ramp**beta)))
    field = field - field.min()
    return field / (field.max() + 1e-12)


def authentic_image(h: int = 96, w: int = 96, seed: int = 7) -> Array:
    """One-light 1/f scene with mild sensor noise (camera-like)."""
    rng = _rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    light = 0.52 + 0.28 * (xx / max(w - 1, 1)) + 0.10 * (yy / max(h - 1, 1))
    light = ndimage.gaussian_filter(light, sigma=3.5, mode="nearest")
    tex = _one_over_f(h, w, rng, beta=1.3)
    luma = np.clip(light * (0.58 + 0.42 * tex), 0.0, 1.0)
    # Warm single illuminant, shared across the frame.
    rgb = np.stack([luma * 1.04, luma * 1.00, luma * 0.93], axis=-1)
    rgb = np.clip(rgb + rng.normal(0.0, 0.011, rgb.shape), 0.0, 1.0)
    return rgb.astype(np.float64)


def deepfake_image(h: int = 96, w: int = 96, seed: int = 21) -> Array:
    """Stacked spatial attacks: upsample lattice, noise mismatch, seam, chroma."""
    rng = _rng(seed)
    base = authentic_image(h, w, seed=seed)
    # 1) Generator-style 2× nearest upsample from a coarse grid.
    coarse = base[::2, ::2]
    up = np.repeat(np.repeat(coarse, 2, axis=0), 2, axis=1)[:h, :w]
    img = 0.55 * base + 0.45 * up
    # 2) Denoised / re-noised center (face-swap residual mismatch).
    cy0, cy1 = h // 4, 3 * h // 4
    cx0, cx1 = w // 4, 3 * w // 4
    img[cy0:cy1, cx0:cx1] = ndimage.gaussian_filter(img[cy0:cy1, cx0:cx1], sigma=1.6)
    img[cy0:cy1, cx0:cx1] = np.clip(
        img[cy0:cy1, cx0:cx1] + rng.normal(0.0, 0.055, img[cy0:cy1, cx0:cx1].shape),
        0.0,
        1.0,
    )
    # 3) Hard illuminant seam (left warm, right cold).
    mid = w // 2
    img[:, mid:, 0] *= 0.72
    img[:, mid:, 2] = np.clip(img[:, mid:, 2] * 1.35, 0.0, 1.0)
    img[:, mid] = np.clip(img[:, mid] + np.array([0.18, -0.04, -0.16]), 0.0, 1.0)
    # 4) Periodic axial grid (FFT fingerprint).
    yy, xx = np.mgrid[0:h, 0:w]
    grid = 0.08 * np.cos(2.0 * np.pi * xx / 4.0) + 0.08 * np.cos(2.0 * np.pi * yy / 4.0)
    img = np.clip(img + grid[..., None], 0.0, 1.0)
    return img.astype(np.float64)


def authentic_video(n: int = 12, h: int = 64, w: int = 64, seed: int = 3) -> Array:
    """Smoothly translating blob on a 1/f background — one exposure."""
    rng = _rng(seed)
    bg = authentic_image(h, w, seed=seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    frames = []
    for t in range(n):
        cx = 18.0 + t * 2.15
        cy = 22.0 + 0.35 * t
        blob = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * 7.5**2))
        frame = np.clip(bg + 0.35 * blob[..., None], 0.0, 1.0)
        frame = np.clip(frame + rng.normal(0.0, 0.008, frame.shape), 0.0, 1.0)
        frames.append(frame)
    return np.stack(frames, axis=0)


def deepfake_video(n: int = 12, h: int = 64, w: int = 64, seed: int = 9) -> Array:
    """Per-frame independent texture + jittered identity (talking-head swap)."""
    rng = _rng(seed)
    frames = []
    for t in range(n):
        # New 1/f field every frame (flicker + identity).
        img = authentic_image(h, w, seed=seed + 17 * t + 3)
        img = deepfake_image(h, w, seed=seed + 31 * t) * 0.65 + img * 0.35
        # Random center identity splash.
        cy0, cy1 = h // 4, 3 * h // 4
        cx0, cx1 = w // 4, 3 * w // 4
        splash = _one_over_f(cy1 - cy0, cx1 - cx0, rng, beta=0.6)
        img[cy0:cy1, cx0:cx1] = 0.35 * img[cy0:cy1, cx0:cx1] + 0.65 * splash[..., None]
        # Mean flicker.
        img = np.clip(img * float(rng.uniform(0.72, 1.22)), 0.0, 1.0)
        frames.append(img)
    return np.stack(frames, axis=0)


def interpolated_video(n: int = 12, h: int = 64, w: int = 64, seed: int = 4) -> Array:
    """Odd frames are blends of neighbors (frame-interpolation artifact)."""
    base = authentic_video(n=n, h=h, w=w, seed=seed)
    out = base.copy()
    for i in range(1, n - 1, 2):
        out[i] = 0.5 * (base[i - 1] + base[i + 1])
    return out


@dataclass
class AVClip:
    audio: Array
    sr: int
    frames: Array
    fps: float


def authentic_av(
    duration_s: float = 0.48,
    sr: int = 16000,
    fps: float = 25.0,
    seed: int = 5,
) -> AVClip:
    """Mouth-proxy blob size follows the audio envelope."""
    pair = make_pair(duration_s=duration_s, sr=sr, f0=120.0, seed=seed)
    audio = pair.audio
    n = max(6, int(round(duration_s * fps)))
    hop = max(1, audio.size // n)
    env = np.array(
        [float(np.sqrt(np.mean(audio[i * hop : (i + 1) * hop] ** 2) + 1e-12)) for i in range(n)],
        dtype=np.float64,
    )
    env = env / (env.max() + 1e-12)
    h = w = 64
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    bg = authentic_image(h, w, seed=seed)
    rng = _rng(seed)
    frames = []
    for t, e in enumerate(env):
        rad = 5.0 + 10.0 * e
        cx = 20.0 + 1.6 * t
        cy = 28.0
        blob = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * rad**2))
        frame = np.clip(bg + (0.20 + 0.45 * e) * blob[..., None], 0.0, 1.0)
        frame = np.clip(frame + rng.normal(0.0, 0.007, frame.shape), 0.0, 1.0)
        frames.append(frame)
    return AVClip(audio=audio, sr=sr, frames=np.stack(frames, axis=0), fps=fps)


def deepfake_av(
    duration_s: float = 0.48,
    sr: int = 16000,
    fps: float = 25.0,
    seed: int = 11,
) -> AVClip:
    """Audio from one utterance; motion from an independent flicker clip."""
    pair = make_pair(duration_s=duration_s, sr=sr, f0=160.0, seed=seed)
    frames = deepfake_video(n=max(6, int(round(duration_s * fps))), h=64, w=64, seed=seed + 4)
    return AVClip(audio=pair.audio, sr=sr, frames=frames, fps=fps)


def pitch_jumped(audio: np.ndarray, sr: int, hop_s: float = 0.08) -> Array:
    """Octave hops every ``hop_s`` — an unnatural source shift."""
    x = np.asarray(audio, dtype=np.float64)
    hop = max(8, int(round(hop_s * sr)))
    y = np.zeros_like(x)
    sign = 1
    for i in range(0, x.size, hop):
        sl = x[i : i + hop]
        if sign > 0:
            y[i : i + sl.size] = sl
        else:
            # Crude octave-up: drop every other sample and hold.
            up = np.repeat(sl[::2], 2)[: sl.size]
            if up.size < sl.size:
                up = np.pad(up, (0, sl.size - up.size))
            y[i : i + sl.size] = up
        sign *= -1
    peak = float(np.max(np.abs(y)) + 1e-12)
    return (y / peak).astype(np.float64)


def pitch_flat(duration_s: float = 1.0, sr: int = 16000, f0: float = 140.0) -> Array:
    """Perfectly periodic pulse train — robotic F0."""
    n = int(duration_s * sr)
    t = np.arange(n, dtype=np.float64) / float(sr)
    phase = np.floor(t * f0)
    pulses = np.diff(phase, prepend=phase[0]) > 0
    y = pulses.astype(np.float64)
    # Fixed resonators, zero jitter.
    from vibelock.synth import vocal_tract

    y = vocal_tract(y, sr, ((700.0, 80.0), (1200.0, 90.0), (2400.0, 120.0)))
    peak = float(np.max(np.abs(y)) + 1e-12)
    return (y / peak).astype(np.float64)


def phase_stretched(audio: np.ndarray, sr: int, rate: float = 1.55) -> Array:
    """Phase-vocoder time-stretch (unnatural horizontal phase)."""
    from scipy import signal as sp

    x = np.asarray(audio, dtype=np.float64)
    nper = 256
    _f, _t, zxx = sp.stft(x, fs=sr, nperseg=nper, noverlap=nper // 2)
    # Stretch by repeating columns (classic cheap vocoder).
    cols = []
    n = zxx.shape[1]
    target = int(round(n * rate))
    idx = np.linspace(0, n - 1, target)
    for i in idx:
        cols.append(zxx[:, int(round(i))])
    z2 = np.stack(cols, axis=1)
    _t, y = sp.istft(z2, fs=sr, nperseg=nper, noverlap=nper // 2)
    y = np.real(y)
    peak = float(np.max(np.abs(y)) + 1e-12)
    return (y / peak).astype(np.float64)
