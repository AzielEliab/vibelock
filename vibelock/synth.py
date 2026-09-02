"""Synthetic physically-plausible dual-channel pairs.

The transfer-function baseline in dual-channel mode is learned from
pairs generated here, NOT from a published human dataset. That fact is
part of the public contract: the baseline is a physics-inspired prior,
not an empirical speaker corpus.

Model (whitepaper § dual-channel / transfer-function consistency):

* A glottal-like pulse train with spectral tilt (source).
* Air channel = source through a cascade of second-order formant
  resonators (a tiny vocal-tract sketch).
* Vibration channel = source through a low-pass bone/tissue coupler
  with a mild low-frequency resonance.

This is a toy biomechanical cartoon. It is enough to define a family of
plausible vibration-to-air maps; it is not a claim about any recorded
human.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy import signal

Array = NDArray[np.float64]


def _rng(seed: int | None) -> np.random.Generator:
    return np.random.default_rng(seed)


def glottal_source(
    n: int,
    sr: int,
    f0: float = 120.0,
    jitter: float = 0.008,
    shimmer: float = 0.04,
    tilt_hz: float = 250.0,
    rng: np.random.Generator | None = None,
) -> Array:
    """Filtered impulse train with mild jitter/shimmer (Rosenberg-ish tilt)."""
    rng = rng or _rng(None)
    t = np.arange(n, dtype=np.float64) / float(sr)
    # Time-varying F0: slow drift + light vibrato, plus cycle jitter.
    vibrato = 1.0 + 0.012 * np.sin(2.0 * np.pi * 5.2 * t)
    drift = 1.0 + 0.03 * (t / max(t[-1], 1e-9) - 0.5)
    inst_f0 = f0 * vibrato * drift
    phase = np.cumsum(inst_f0 / sr)
    # Emit a pulse each time phase crosses an integer.
    crossed = np.diff(np.floor(phase), prepend=phase[0])
    pulses = (crossed > 0).astype(np.float64)
    if jitter > 0:
        # Nudge non-zero pulse amplitudes; timing jitter via F0 already.
        mag = 1.0 + shimmer * rng.normal(0.0, 1.0, size=n)
        pulses = pulses * mag
        # Small sample-level timing noise on pulse locations.
        shift = rng.integers(-1, 2, size=n) if jitter > 0 else 0
        if np.ndim(shift) > 0:
            idx = np.nonzero(pulses)[0]
            for i in idx:
                s = int(shift[i])
                if s != 0 and 0 <= i + s < n:
                    pulses[i + s] += pulses[i] * 0.15
    # Two-pole spectral tilt ~ glottal roll-off.
    nyq = 0.5 * sr
    cutoff = min(max(tilt_hz, 40.0), 0.45 * nyq)
    sos = signal.butter(2, cutoff / nyq, btype="low", output="sos")
    source = signal.sosfilt(sos, pulses)
    # Gentle high-pass to remove DC.
    sos_hp = signal.butter(1, 40.0 / nyq, btype="high", output="sos")
    source = signal.sosfilt(sos_hp, source)
    peak = np.max(np.abs(source)) + 1e-12
    return (source / peak).astype(np.float64)


def resonator(x: np.ndarray, sr: int, freq: float, bw: float) -> Array:
    """Two-pole formant resonator (unity b0, conjugate poles)."""
    x = np.asarray(x, dtype=np.float64)
    r = float(np.exp(-np.pi * bw / sr))
    theta = 2.0 * np.pi * freq / sr
    a = [1.0, -2.0 * r * np.cos(theta), r * r]
    b = [1.0]
    return np.asarray(signal.lfilter(b, a, x), dtype=np.float64)


def vocal_tract(
    source: np.ndarray,
    sr: int,
    formants: tuple[tuple[float, float], ...],
) -> Array:
    y = np.asarray(source, dtype=np.float64)
    for freq, bw in formants:
        y = resonator(y, sr, freq, bw)
    peak = np.max(np.abs(y)) + 1e-12
    return (y / peak).astype(np.float64)


def bone_coupling(
    source: np.ndarray,
    sr: int,
    cutoff_hz: float = 1200.0,
    resonance_hz: float = 400.0,
    resonance_bw: float = 180.0,
) -> Array:
    """Tissue/bone coupler: low-pass plus a mild jaw/skull resonance."""
    x = np.asarray(source, dtype=np.float64)
    nyq = 0.5 * sr
    cut = min(max(cutoff_hz, 80.0), 0.45 * nyq)
    sos = signal.butter(3, cut / nyq, btype="low", output="sos")
    y = signal.sosfilt(sos, x)
    y = resonator(y, sr, resonance_hz, resonance_bw)
    peak = np.max(np.abs(y)) + 1e-12
    return (y / peak).astype(np.float64)


DEFAULT_FORMANTS: tuple[tuple[float, float], ...] = (
    (500.0, 70.0),
    (1500.0, 100.0),
    (2500.0, 140.0),
)


@dataclass
class DualPair:
    """A synthetic air + vibration pair sharing one glottal source."""

    audio: Array
    vibration: Array
    sr: int
    f0: float
    formants: tuple[tuple[float, float], ...]


def make_pair(
    duration_s: float = 1.2,
    sr: int = 16000,
    f0: float = 120.0,
    formants: tuple[tuple[float, float], ...] | None = None,
    bone_cutoff_hz: float = 1200.0,
    air_delay_s: float = 0.0025,
    noise_db: float = -35.0,
    seed: int | None = None,
) -> DualPair:
    """Build one physically-plausible dual-channel pair.

    ``air_delay_s`` models vocal-tract group delay (air lags the source
    slightly). Independent sensor noise is added at ``noise_db``.
    """
    rng = _rng(seed)
    formants = formants or DEFAULT_FORMANTS
    n = int(round(duration_s * sr))
    n = max(n, 256)
    source = glottal_source(n, sr, f0=f0, rng=rng)
    audio = vocal_tract(source, sr, formants)
    vibration = bone_coupling(source, sr, cutoff_hz=bone_cutoff_hz)
    delay = int(round(air_delay_s * sr))
    if delay > 0:
        delayed = np.zeros_like(audio)
        delayed[delay:] = audio[: n - delay]
        audio = delayed
    noise_gain = 10.0 ** (noise_db / 20.0)
    audio = audio + noise_gain * rng.normal(0.0, 1.0, size=n)
    vibration = vibration + noise_gain * rng.normal(0.0, 1.0, size=n)
    # Short cosine fade-in/out so offset-decay tests see a real ending,
    # not an abrupt clip (and not a reverb tail).
    fade = min(int(0.04 * sr), n // 8)
    if fade > 2:
        ramp = 0.5 - 0.5 * np.cos(np.linspace(0.0, np.pi, fade))
        audio[:fade] *= ramp
        audio[-fade:] *= ramp[::-1]
        vibration[:fade] *= ramp
        vibration[-fade:] *= ramp[::-1]
    # Peak-normalize independently (contact mic vs air mic gains differ).
    audio = audio / (np.max(np.abs(audio)) + 1e-12)
    vibration = vibration / (np.max(np.abs(vibration)) + 1e-12)
    return DualPair(
        audio=audio.astype(np.float64),
        vibration=vibration.astype(np.float64),
        sr=sr,
        f0=f0,
        formants=formants,
    )


def formant_family(rng: np.random.Generator) -> tuple[tuple[float, float], ...]:
    """Sample a plausible 3-formant sketch (not a human dataset)."""
    f1 = float(rng.uniform(350.0, 750.0))
    f2 = float(rng.uniform(900.0, 2100.0))
    f3 = float(rng.uniform(2100.0, 3200.0))
    if f2 <= f1 + 150:
        f2 = f1 + 200
    if f3 <= f2 + 150:
        f3 = f2 + 250
    b1 = float(rng.uniform(50.0, 110.0))
    b2 = float(rng.uniform(70.0, 150.0))
    b3 = float(rng.uniform(90.0, 200.0))
    return ((f1, b1), (f2, b2), (f3, b3))


def bootstrap_pairs(
    n_pairs: int = 24,
    sr: int = 16000,
    duration_s: float = 0.9,
    seed: int = 202607,
) -> list[DualPair]:
    """Draw a synthetic bootstrap ensemble for the transfer-function prior."""
    rng = _rng(seed)
    pairs: list[DualPair] = []
    for i in range(n_pairs):
        f0 = float(rng.uniform(85.0, 230.0))
        formants = formant_family(rng)
        cutoff = float(rng.uniform(800.0, 1600.0))
        delay = float(rng.uniform(0.001, 0.006))
        pairs.append(
            make_pair(
                duration_s=duration_s,
                sr=sr,
                f0=f0,
                formants=formants,
                bone_cutoff_hz=cutoff,
                air_delay_s=delay,
                noise_db=float(rng.uniform(-40.0, -28.0)),
                seed=int(seed + 17 * i + 3),
            )
        )
    return pairs



def sample_tone(
    duration_s: float = 0.8,
    sr: int = 16000,
    freq: float = 440.0,
    amplitude: float = 0.2,
) -> Array:
    """Short 440 Hz tone for the UI sample button. Not speech."""
    n = max(1, int(float(duration_s) * int(sr)))
    t = np.arange(n, dtype=np.float64) / float(sr)
    attack = np.minimum(1.0, t / 0.02)
    tail = float(duration_s) - t
    release = np.minimum(1.0, np.maximum(0.0, tail / 0.08))
    env = attack * release
    return (float(amplitude) * env * np.sin(2.0 * np.pi * float(freq) * t)).astype(np.float64)
