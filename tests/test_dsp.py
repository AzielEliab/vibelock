"""Unit tests for DSP primitives (whitepaper building blocks)."""

from __future__ import annotations

import numpy as np

from vibelock import dsp
from vibelock.synth import make_pair, resonator


def test_coherence_high_for_linearly_filtered_copy():
    sr = 16000
    rng = np.random.default_rng(0)
    x = rng.normal(0, 1, sr)
    y = dsp.bandpass(x, sr, 80.0, 2000.0)
    freqs, cxy = dsp.magnitude_squared_coherence(x, y, sr)
    mean = dsp.band_mean(freqs, cxy, 100.0, 1500.0)
    assert mean > 0.7


def test_coherence_low_for_independent_noise():
    sr = 16000
    rng = np.random.default_rng(1)
    x = rng.normal(0, 1, sr)
    y = rng.normal(0, 1, sr)
    freqs, cxy = dsp.magnitude_squared_coherence(x, y, sr)
    mean = dsp.band_mean(freqs, cxy, 100.0, 1500.0)
    assert mean < 0.25


def test_gcc_phat_recovers_known_delay():
    sr = 16000
    pair = make_pair(duration_s=0.8, sr=sr, seed=4)
    delay_s = 0.007
    n = int(round(delay_s * sr))
    y = np.concatenate([np.zeros(n), pair.audio[: pair.audio.size - n]])
    est = dsp.gcc_phat_delay(pair.audio, y, sr)
    assert abs(est - delay_s) < 0.002


def test_lpc_formants_near_resonator_frequency():
    sr = 16000
    rng = np.random.default_rng(2)
    src = rng.normal(0, 1, sr)
    y = resonator(src, sr, 1000.0, 80.0)
    a = dsp.lpc_coefficients(y[:2048] * np.hanning(2048), order=12)
    freqs, _bw = dsp.formants_from_lpc(a, sr, n_formants=3)
    assert freqs.size >= 1
    assert np.min(np.abs(freqs - 1000.0)) < 150.0


def test_hilbert_envelope_tracks_amplitude():
    sr = 8000
    t = np.arange(sr, dtype=np.float64) / sr
    env_true = 0.2 + 0.8 * t
    x = env_true * np.sin(2 * np.pi * 200 * t)
    env = dsp.hilbert_envelope(x)
    # Skip edges (Hilbert edge effects).
    mid = slice(200, -200)
    corr = np.corrcoef(env_true[mid], env[mid])[0, 1]
    assert corr > 0.95


def test_exponential_decay_fit_recovers_tau():
    sr = 16000
    tau = 0.025
    t = np.arange(int(0.12 * sr), dtype=np.float64) / sr
    x = np.exp(-t / tau) * np.sin(2 * np.pi * 400 * t)
    fits = dsp.decay_profiles(x, sr, n_peaks=3, tail_ms=80.0)
    assert fits
    # At least one fit should be in the right ballpark.
    taus = [f.tau_s for f in fits]
    assert any(abs(v - tau) / tau < 0.6 for v in taus)


def test_as_mono_float_mixes_stereo():
    stereo = np.stack([np.ones(10), np.zeros(10)], axis=1)
    mono = dsp.as_mono_float(stereo)
    assert mono.shape == (10,)
    assert np.allclose(mono, 0.5)
