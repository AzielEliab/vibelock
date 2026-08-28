"""Audio I/O. WAV only, numpy + scipy, no cloud, no identity.

Whitepaper § privacy: local processing, no STT, do not retain raw audio
by default. This module loads a file into memory for analysis and returns
float arrays; it never writes recordings unless the caller asks.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from scipy.io import wavfile

from vibelock.dsp import as_mono_float, resample

Array = NDArray[np.float64]


def _pcm_to_float(data: np.ndarray) -> Array:
    data = np.asarray(data)
    if np.issubdtype(data.dtype, np.floating):
        arr = data.astype(np.float64)
        peak = np.max(np.abs(arr)) if arr.size else 1.0
        if peak > 8.0:
            arr = arr / max(peak, 1.0)
        return arr
    info = np.iinfo(data.dtype)
    scale = float(max(abs(info.min), info.max))
    return data.astype(np.float64) / scale


def load_audio(path: str | Path, target_sr: int | None = None) -> tuple[Array, int]:
    """Load a WAV file as mono float64 in roughly [-1, 1].

    ``target_sr`` resamples when set. Stereo is mixed down. The file is
    not kept after this function returns.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Audio file not found: {path}")
    sr, data = wavfile.read(path)
    arr = _pcm_to_float(data)
    arr = as_mono_float(arr)
    sr = int(sr)
    if target_sr is not None and int(target_sr) != sr:
        arr = resample(arr, sr, int(target_sr))
        sr = int(target_sr)
    return arr, sr


def write_wav(path: str | Path, audio: np.ndarray, sr: int) -> None:
    """Write a 16-bit PCM WAV (used by examples / tests, not by analyze)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    arr = as_mono_float(audio)
    peak = np.max(np.abs(arr)) + 1e-12
    pcm = np.clip(arr / peak, -1.0, 1.0)
    pcm16 = (pcm * 32767.0).astype(np.int16)
    wavfile.write(str(path), int(sr), pcm16)


def match_lengths(*arrays: np.ndarray) -> list[Array]:
    n = min(a.size for a in arrays)
    return [as_mono_float(a)[:n] for a in arrays]
