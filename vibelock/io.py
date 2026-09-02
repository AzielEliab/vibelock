"""Audio I/O. Local files only. No cloud, no identity, no telemetry.

WAV always. FLAC/MP3 only when an optional decoder (soundfile) is present.
Rejects non-audio and truncated files with plain language. Hard max size.
"""

from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from scipy.io import wavfile

from vibelock.debug import log as dlog
from vibelock.dsp import as_mono_float, resample

Array = NDArray[np.float64]

MAX_AUDIO_BYTES = 12 * 1024 * 1024

PLAIN_NOT_AUDIO = "That file is not audio. Please add a WAV file."
PLAIN_TOO_BIG = "That file is too big. Please use a smaller recording."
PLAIN_TRUNCATED = "That audio file looks broken or cut off. Try another file."
PLAIN_WAV_ONLY = "This build can only read WAV files. Please add a WAV file."
PLAIN_EMPTY = "That file is empty. Please add a real audio file."

_NON_AUDIO_PREFIXES = (
    b"\x89PNG\r\n\x1a\n",
    b"%PDF-",
    b"\xff\xd8\xff",
    b"GIF87a",
    b"GIF89a",
    b"PK\x03\x04",
    b"<!DOC",
    b"<html",
    b"<?xml",
)


class AudioError(ValueError):
    """Kid-plain audio problem. The UI and CLI print this string as-is."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def _soundfile_formats() -> set[str]:
    try:
        import soundfile as sf  # type: ignore[import-untyped]
    except ImportError:
        return set()
    try:
        fmts = {str(k).upper() for k in sf.available_formats()}
    except Exception:  # noqa: BLE001 — optional decoder probe
        return set()
    found: set[str] = set()
    if "FLAC" in fmts:
        found.add("flac")
    if "MP3" in fmts:
        found.add("mp3")
    return found


def extra_formats() -> tuple[str, ...]:
    return tuple(sorted(_soundfile_formats()))


def supported_suffixes() -> tuple[str, ...]:
    extras = [f".{name}" for name in extra_formats()]
    return tuple([".wav", *extras])


def accept_attr() -> str:
    parts = [".wav", "audio/wav"]
    extras = set(extra_formats())
    if "flac" in extras:
        parts.extend([".flac", "audio/flac"])
    if "mp3" in extras:
        parts.extend([".mp3", "audio/mpeg"])
    return ",".join(parts)


def not_audio_message() -> str:
    extras = extra_formats()
    if extras:
        names = "WAV, " + ", ".join(n.upper() for n in extras)
        return f"That file is not audio. Please add a {names} file."
    return PLAIN_NOT_AUDIO


def sniff_audio(raw: bytes, name: str = "") -> str:
    """Return 'wav' / 'flac' / 'mp3' or '' if this is not audio."""
    if not raw:
        return ""
    head = raw[:16]
    for prefix in _NON_AUDIO_PREFIXES:
        if head.startswith(prefix) or raw.lstrip()[: len(prefix)].lower().startswith(
            prefix.lower()
        ):
            return ""
    if len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WAVE":
        return "wav"
    if len(raw) >= 4 and raw[:4] == b"RIFF":
        # Truncated RIFF — still treat as wav so decode can say "cut off".
        return "wav"
    if len(raw) >= 4 and raw[:4] == b"fLaC":
        return "flac"
    if len(raw) >= 3 and raw[:3] == b"ID3":
        return "mp3"
    if len(raw) >= 2 and raw[0] == 0xFF and (raw[1] & 0xE0) == 0xE0:
        return "mp3"
    suffix = Path(name).suffix.lower()
    if suffix in {".wav", ".flac", ".mp3"}:
        return suffix[1:]
    return ""


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


def _read_wav_bytes(raw: bytes) -> tuple[Array, int]:
    if len(raw) < 44:
        raise AudioError(PLAIN_TRUNCATED)
    try:
        sr, data = wavfile.read(BytesIO(raw))
    except (ValueError, EOFError, OSError) as exc:
        raise AudioError(PLAIN_TRUNCATED) from exc
    except Exception as exc:  # noqa: BLE001 — never crash the UI on a bad WAV
        dlog(f"wav decode error: {exc!r}")
        raise AudioError(PLAIN_TRUNCATED) from exc
    arr = np.asarray(data)
    if arr.size == 0:
        raise AudioError(PLAIN_TRUNCATED)
    return as_mono_float(_pcm_to_float(arr)), int(sr)


def _read_with_soundfile(raw: bytes, kind: str) -> tuple[Array, int]:
    extras = extra_formats()
    if kind not in extras:
        raise AudioError(PLAIN_WAV_ONLY)
    try:
        import soundfile as sf  # type: ignore[import-untyped]

        data, sr = sf.read(BytesIO(raw), always_2d=False)
    except Exception as exc:  # noqa: BLE001
        dlog(f"soundfile decode error: {exc!r}")
        raise AudioError(PLAIN_TRUNCATED) from exc
    arr = np.asarray(data)
    if arr.size == 0:
        raise AudioError(PLAIN_TRUNCATED)
    return as_mono_float(_pcm_to_float(arr)), int(sr)


def decode_audio_bytes(
    raw: bytes,
    name: str = "",
    *,
    target_sr: int | None = None,
    max_bytes: int = MAX_AUDIO_BYTES,
) -> tuple[Array, int]:
    """Decode in-memory audio. Never crashes on truncated or foreign bytes."""
    dlog(f"decode name={name!r} n={len(raw)}")
    if len(raw) > int(max_bytes):
        raise AudioError(PLAIN_TOO_BIG)
    if not raw:
        raise AudioError(PLAIN_EMPTY)
    kind = sniff_audio(raw, name)
    if not kind:
        raise AudioError(not_audio_message())
    if kind == "wav":
        arr, sr = _read_wav_bytes(raw)
    elif kind in {"flac", "mp3"}:
        arr, sr = _read_with_soundfile(raw, kind)
    else:
        raise AudioError(not_audio_message())
    if target_sr is not None and int(target_sr) != sr:
        arr = resample(arr, sr, int(target_sr))
        sr = int(target_sr)
    dlog(f"decoded kind={kind} sr={sr} samples={arr.size}")
    return arr, sr


def load_audio(
    path: str | Path,
    target_sr: int | None = None,
    *,
    max_bytes: int = MAX_AUDIO_BYTES,
) -> tuple[Array, int]:
    """Load a local audio file as mono float64 in roughly [-1, 1].

    ``target_sr`` resamples when set. Stereo is mixed down. The file is
    not kept after this function returns. Never uploads anything.
    """
    audio, sr, _meta = load_audio_ex(path, target_sr=target_sr, max_bytes=max_bytes)
    return audio, sr


def load_audio_ex(
    path: str | Path,
    target_sr: int | None = None,
    *,
    max_bytes: int = MAX_AUDIO_BYTES,
) -> tuple[Array, int, dict]:
    """Like ``load_audio`` plus ``{sha256, filename, n_bytes, format}``."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Audio file not found: {path}")
    size = path.stat().st_size
    dlog(f"load {path} size={size}")
    if size > int(max_bytes):
        raise AudioError(PLAIN_TOO_BIG)
    raw = path.read_bytes()
    digest = sha256_bytes(raw)
    arr, sr = decode_audio_bytes(
        raw, name=path.name, target_sr=target_sr, max_bytes=max_bytes
    )
    meta = {
        "path": str(path),
        "filename": path.name,
        "sha256": digest,
        "n_bytes": len(raw),
        "format": sniff_audio(raw, path.name) or "unknown",
    }
    return arr, sr, meta


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
