"""Image and video I/O for the VibeLock A/V deepfake engine.

PNG and PPM always (stdlib zlib + numpy). JPEG only when Pillow is
present. Video is a frame stack: a directory of stills, a ``.vlvd``
container, or a ``.npy`` array. No cloud, no identity, no telemetry.

This module never decodes MP4/H.264 — that would pull a codec stack
the core package refuses. A talking-head clip is frames + optional WAV.
"""

from __future__ import annotations

import struct
import zlib
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from vibelock.debug import log as dlog
from vibelock.io import AudioError, MAX_AUDIO_BYTES, decode_audio_bytes, sniff_audio

Array = NDArray[np.float64]

MAX_MEDIA_BYTES = 16 * 1024 * 1024
MAX_PIXELS = 4 * 1024 * 1024
MAX_FRAMES = 180
MAX_EDGE = 2048

PNG_SIG = b"\x89PNG\r\n\x1a\n"
PPM_PLAIN_TOO_BIG = "That file is too big. Please use a smaller photo or clip."
PPM_PLAIN_NOT_MEDIA = "That file is not audio, an image, or a frame stack VibeLock can read."
PPM_PLAIN_BROKEN = "That image or clip looks broken or cut off. Try another file."
PPM_PLAIN_EMPTY = "That file is empty. Please add a real recording or photo."
JPEG_NEEDS_PILLOW = "This build can read PNG and PPM. JPEG needs the optional Pillow package."

VLVD_MAGIC = b"VLVD"
VLVD_VERSION = 1


class MediaError(ValueError):
    """Kid-plain media problem. The UI and CLI print this string as-is."""


def _as_error(exc: Exception) -> MediaError:
    if isinstance(exc, MediaError):
        return exc
    if isinstance(exc, AudioError):
        return MediaError(str(exc))
    return MediaError(PPM_PLAIN_BROKEN)


def to_rgb01(image: np.ndarray) -> Array:
    """Return HxWx3 float64 in [0, 1]. Gray is stacked; alpha is dropped."""
    arr = np.asarray(image)
    if arr.size == 0:
        raise MediaError(PPM_PLAIN_BROKEN)
    if np.issubdtype(arr.dtype, np.integer):
        info = np.iinfo(arr.dtype)
        arr = arr.astype(np.float64) / float(max(abs(info.max), 1))
    else:
        arr = arr.astype(np.float64)
        peak = float(np.max(arr)) if arr.size else 1.0
        if peak > 1.5:
            arr = arr / 255.0
    arr = np.clip(arr, 0.0, 1.0)
    if arr.ndim == 2:
        arr = np.stack([arr, arr, arr], axis=-1)
    elif arr.ndim == 3 and arr.shape[-1] == 1:
        arr = np.repeat(arr, 3, axis=-1)
    elif arr.ndim == 3 and arr.shape[-1] == 4:
        arr = arr[..., :3]
    elif arr.ndim == 3 and arr.shape[-1] == 3:
        pass
    else:
        raise MediaError(PPM_PLAIN_BROKEN)
    h, w, _ = arr.shape
    if h * w > MAX_PIXELS or h > MAX_EDGE or w > MAX_EDGE:
        raise MediaError(PPM_PLAIN_TOO_BIG)
    return np.ascontiguousarray(arr, dtype=np.float64)


def to_gray01(image: np.ndarray) -> Array:
    rgb = to_rgb01(image)
    return (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]).astype(
        np.float64
    )


def frames_to_rgb01(frames: np.ndarray) -> Array:
    """Return TxHxWx3 float64 in [0, 1]."""
    arr = np.asarray(frames)
    if arr.ndim == 3:
        arr = arr[..., None]
    if arr.ndim != 4:
        raise MediaError(PPM_PLAIN_BROKEN)
    t = int(arr.shape[0])
    if t < 1:
        raise MediaError(PPM_PLAIN_BROKEN)
    if t > MAX_FRAMES:
        arr = arr[:MAX_FRAMES]
    out = [to_rgb01(frame) for frame in arr]
    return np.stack(out, axis=0)


def sniff_media(raw: bytes, name: str = "") -> str:
    """Return audio / image / video or ''."""
    if not raw:
        return ""
    if raw.startswith(PNG_SIG) or raw[:2] == b"P6" or raw[:2] == b"P5":
        return "image"
    if raw[:2] == b"\xff\xd8":
        return "image"
    if raw.startswith(VLVD_MAGIC):
        return "video"
    if raw[:6] == b"\x93NUMPY":
        return "ndarray"
    kind = sniff_audio(raw, name)
    if kind:
        return "audio"
    suffix = Path(name).suffix.lower()
    if suffix in {".png", ".ppm", ".pgm", ".jpg", ".jpeg"}:
        return "image"
    if suffix in {".vlvd", ".npy"}:
        return "video"
    if suffix in {".wav", ".flac", ".mp3"}:
        return "audio"
    return ""


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def encode_png(image: np.ndarray) -> bytes:
    """Encode an 8-bit RGB PNG (filter None)."""
    rgb = to_rgb01(image)
    h, w, _ = rgb.shape
    pixels = np.clip(np.rint(rgb * 255.0), 0, 255).astype(np.uint8)
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw.extend(pixels[y].tobytes())
    compressed = zlib.compress(bytes(raw), level=6)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return PNG_SIG + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", compressed) + _png_chunk(
        b"IEND", b""
    )


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _unfilter_scanline(ftype: int, line: bytearray, prev: bytes, bpp: int) -> bytes:
    n = len(line)
    out = bytearray(n)
    if ftype == 0:
        return bytes(line)
    if ftype == 1:
        for i in range(n):
            left = out[i - bpp] if i >= bpp else 0
            out[i] = (line[i] + left) & 255
        return bytes(out)
    if ftype == 2:
        for i in range(n):
            up = prev[i] if prev else 0
            out[i] = (line[i] + up) & 255
        return bytes(out)
    if ftype == 3:
        for i in range(n):
            left = out[i - bpp] if i >= bpp else 0
            up = prev[i] if prev else 0
            out[i] = (line[i] + ((left + up) // 2)) & 255
        return bytes(out)
    if ftype == 4:
        for i in range(n):
            left = out[i - bpp] if i >= bpp else 0
            up = prev[i] if prev else 0
            ul = prev[i - bpp] if prev and i >= bpp else 0
            out[i] = (line[i] + _paeth(left, up, ul)) & 255
        return bytes(out)
    raise MediaError(PPM_PLAIN_BROKEN)


def decode_png(raw: bytes) -> Array:
    if not raw.startswith(PNG_SIG):
        raise MediaError(PPM_PLAIN_BROKEN)
    pos = 8
    width = height = bit_depth = color_type = interlace = None
    idat = bytearray()
    while pos + 12 <= len(raw):
        (length,) = struct.unpack(">I", raw[pos : pos + 4])
        tag = raw[pos + 4 : pos + 8]
        data = raw[pos + 8 : pos + 8 + length]
        if pos + 12 + length > len(raw):
            raise MediaError(PPM_PLAIN_BROKEN)
        crc_got = struct.unpack(">I", raw[pos + 8 + length : pos + 12 + length])[0]
        crc_exp = zlib.crc32(tag + data) & 0xFFFFFFFF
        if crc_got != crc_exp:
            raise MediaError(PPM_PLAIN_BROKEN)
        pos += 12 + length
        if tag == b"IHDR":
            width, height, bit_depth, color_type, _comp, _filt, interlace = struct.unpack(
                ">IIBBBBB", data
            )
        elif tag == b"IDAT":
            idat.extend(data)
        elif tag == b"IEND":
            break
    if width is None or height is None or not idat:
        raise MediaError(PPM_PLAIN_BROKEN)
    if bit_depth != 8 or interlace != 0 or color_type not in {0, 2, 4, 6}:
        raise MediaError("That PNG uses a color type VibeLock cannot read. Use 8-bit RGB or gray.")
    if width * height > MAX_PIXELS or width > MAX_EDGE or height > MAX_EDGE:
        raise MediaError(PPM_PLAIN_TOO_BIG)
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[color_type]
    bpp = channels
    try:
        inflated = zlib.decompress(bytes(idat))
    except zlib.error as exc:
        raise MediaError(PPM_PLAIN_BROKEN) from exc
    stride = width * channels
    expected = height * (1 + stride)
    if len(inflated) < expected:
        raise MediaError(PPM_PLAIN_BROKEN)
    rows = []
    prev = b""
    cursor = 0
    for _ in range(height):
        ftype = inflated[cursor]
        line = bytearray(inflated[cursor + 1 : cursor + 1 + stride])
        cursor += 1 + stride
        recon = _unfilter_scanline(ftype, line, prev, bpp)
        prev = recon
        rows.append(np.frombuffer(recon, dtype=np.uint8))
    pixels = np.vstack(rows).reshape(height, width, channels)
    return to_rgb01(pixels)


def encode_ppm(image: np.ndarray) -> bytes:
    rgb = to_rgb01(image)
    h, w, _ = rgb.shape
    pixels = np.clip(np.rint(rgb * 255.0), 0, 255).astype(np.uint8)
    header = f"P6\n{w} {h}\n255\n".encode("ascii")
    return header + pixels.tobytes()


def decode_ppm(raw: bytes) -> Array:
    if raw[:2] not in {b"P5", b"P6"}:
        raise MediaError(PPM_PLAIN_BROKEN)
    kind = raw[:2]
    # Skip comments after magic.
    i = 2
    if i < len(raw) and raw[i : i + 1] in {b"\r", b"\n", b" "}:
        i += 1
    tokens: list[bytes] = []
    buf = b""
    while i < len(raw) and len(tokens) < 3:
        c = raw[i : i + 1]
        if c == b"#":
            while i < len(raw) and raw[i : i + 1] not in {b"\n", b"\r"}:
                i += 1
            continue
        if c.isspace():
            if buf:
                tokens.append(buf)
                buf = b""
            i += 1
            continue
        buf += c
        i += 1
    if buf and len(tokens) < 3:
        tokens.append(buf)
        i += 1
    if len(tokens) < 3:
        raise MediaError(PPM_PLAIN_BROKEN)
    try:
        w, h, maxv = (int(tokens[0]), int(tokens[1]), int(tokens[2]))
    except ValueError as exc:
        raise MediaError(PPM_PLAIN_BROKEN) from exc
    if w <= 0 or h <= 0 or maxv <= 0 or w * h > MAX_PIXELS:
        raise MediaError(PPM_PLAIN_TOO_BIG)
    payload = raw[i:]
    if kind == b"P6":
        need = w * h * 3
        if len(payload) < need:
            raise MediaError(PPM_PLAIN_BROKEN)
        pixels = np.frombuffer(payload[:need], dtype=np.uint8).reshape(h, w, 3)
    else:
        need = w * h
        if len(payload) < need:
            raise MediaError(PPM_PLAIN_BROKEN)
        pixels = np.frombuffer(payload[:need], dtype=np.uint8).reshape(h, w)
    return to_rgb01(pixels)


def decode_jpeg(raw: bytes) -> Array:
    try:
        from PIL import Image  # type: ignore[import-untyped]
    except ImportError as exc:
        raise MediaError(JPEG_NEEDS_PILLOW) from exc
    try:
        img = Image.open(BytesIO(raw))
        img = img.convert("RGB")
        arr = np.asarray(img, dtype=np.uint8)
    except Exception as exc:  # noqa: BLE001
        raise MediaError(PPM_PLAIN_BROKEN) from exc
    return to_rgb01(arr)


def decode_image_bytes(raw: bytes, name: str = "") -> Array:
    if not raw:
        raise MediaError(PPM_PLAIN_EMPTY)
    if len(raw) > MAX_MEDIA_BYTES:
        raise MediaError(PPM_PLAIN_TOO_BIG)
    if raw.startswith(PNG_SIG):
        return decode_png(raw)
    if raw[:2] in {b"P5", b"P6"}:
        return decode_ppm(raw)
    if raw[:2] == b"\xff\xd8":
        return decode_jpeg(raw)
    suffix = Path(name).suffix.lower()
    if suffix == ".png":
        return decode_png(raw)
    if suffix in {".ppm", ".pgm"}:
        return decode_ppm(raw)
    if suffix in {".jpg", ".jpeg"}:
        return decode_jpeg(raw)
    raise MediaError(PPM_PLAIN_NOT_MEDIA)


def encode_vlvd(frames: np.ndarray, fps: float = 25.0) -> bytes:
    stack = frames_to_rgb01(frames)
    t, h, w, c = stack.shape
    pixels = np.clip(np.rint(stack * 255.0), 0, 255).astype(np.uint8)
    header = VLVD_MAGIC + struct.pack("<IIiiif", VLVD_VERSION, t, h, w, c, float(fps))
    return header + pixels.tobytes()


def decode_vlvd(raw: bytes) -> tuple[Array, float]:
    if not raw.startswith(VLVD_MAGIC) or len(raw) < 24:
        raise MediaError(PPM_PLAIN_BROKEN)
    version, t, h, w, c, fps = struct.unpack("<IIiiif", raw[4:24])
    if version != VLVD_VERSION or t < 1 or h < 2 or w < 2 or c not in {1, 3}:
        raise MediaError(PPM_PLAIN_BROKEN)
    if t > MAX_FRAMES or h * w > MAX_PIXELS or h > MAX_EDGE or w > MAX_EDGE:
        raise MediaError(PPM_PLAIN_TOO_BIG)
    need = t * h * w * c
    payload = raw[24:]
    if len(payload) < need:
        raise MediaError(PPM_PLAIN_BROKEN)
    pixels = np.frombuffer(payload[:need], dtype=np.uint8).reshape(t, h, w, c)
    return frames_to_rgb01(pixels), float(fps)


def decode_npy_frames(raw: bytes) -> tuple[Array, float]:
    try:
        arr = np.load(BytesIO(raw), allow_pickle=False)
    except Exception as exc:  # noqa: BLE001
        raise MediaError(PPM_PLAIN_BROKEN) from exc
    if arr.ndim == 2 or (arr.ndim == 3 and arr.shape[-1] in {1, 3, 4}):
        return frames_to_rgb01(arr[None, ...]), 1.0
    if arr.ndim in {3, 4}:
        return frames_to_rgb01(arr), 25.0
    raise MediaError(PPM_PLAIN_BROKEN)


def decode_video_bytes(raw: bytes, name: str = "") -> tuple[Array, float]:
    if not raw:
        raise MediaError(PPM_PLAIN_EMPTY)
    if len(raw) > MAX_MEDIA_BYTES:
        raise MediaError(PPM_PLAIN_TOO_BIG)
    if raw.startswith(VLVD_MAGIC):
        return decode_vlvd(raw)
    if raw[:6] == b"\x93NUMPY":
        return decode_npy_frames(raw)
    suffix = Path(name).suffix.lower()
    if suffix == ".vlvd":
        return decode_vlvd(raw)
    if suffix == ".npy":
        return decode_npy_frames(raw)
    # A single still is a one-frame clip.
    if sniff_media(raw, name) == "image":
        return frames_to_rgb01(decode_image_bytes(raw, name)[None, ...]), 1.0
    raise MediaError(PPM_PLAIN_NOT_MEDIA)


def load_image(path: str | Path) -> tuple[Array, dict[str, Any]]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Image file not found: {path}")
    raw = path.read_bytes()
    if len(raw) > MAX_MEDIA_BYTES:
        raise MediaError(PPM_PLAIN_TOO_BIG)
    img = decode_image_bytes(raw, name=path.name)
    from vibelock.io import sha256_bytes

    meta = {
        "path": str(path),
        "filename": path.name,
        "sha256": sha256_bytes(raw),
        "n_bytes": len(raw),
        "kind": "image",
        "shape": list(img.shape),
    }
    return img, meta


def load_video(path: str | Path, *, fps: float | None = None) -> tuple[Array, float, dict[str, Any]]:
    path = Path(path)
    from vibelock.io import sha256_bytes

    if path.is_dir():
        files = sorted(
            p
            for p in path.iterdir()
            if p.is_file() and p.suffix.lower() in {".png", ".ppm", ".pgm", ".jpg", ".jpeg"}
        )
        if not files:
            raise MediaError("That folder has no PNG or PPM frames.")
        frames = [decode_image_bytes(p.read_bytes(), name=p.name) for p in files[:MAX_FRAMES]]
        stack = frames_to_rgb01(np.stack(frames, axis=0))
        rate = float(fps or 25.0)
        digest = sha256_bytes(b"".join(p.read_bytes()[:64] for p in files[:8]))
        meta = {
            "path": str(path),
            "filename": path.name,
            "sha256": digest,
            "n_bytes": sum(p.stat().st_size for p in files),
            "kind": "video",
            "n_frames": int(stack.shape[0]),
            "fps": rate,
        }
        return stack, rate, meta
    if not path.is_file():
        raise FileNotFoundError(f"Video file not found: {path}")
    raw = path.read_bytes()
    stack, file_fps = decode_video_bytes(raw, name=path.name)
    rate = float(fps or file_fps or 25.0)
    meta = {
        "path": str(path),
        "filename": path.name,
        "sha256": sha256_bytes(raw),
        "n_bytes": len(raw),
        "kind": "video",
        "n_frames": int(stack.shape[0]),
        "fps": rate,
    }
    return stack, rate, meta


def decode_any_bytes(
    raw: bytes,
    name: str = "",
) -> dict[str, Any]:
    """Dispatch bytes to audio / image / video. Raises MediaError."""
    if not raw:
        raise MediaError(PPM_PLAIN_EMPTY)
    if len(raw) > max(MAX_MEDIA_BYTES, MAX_AUDIO_BYTES):
        raise MediaError(PPM_PLAIN_TOO_BIG)
    kind = sniff_media(raw, name)
    dlog(f"sniff name={name!r} kind={kind} n={len(raw)}")
    if kind == "audio":
        audio, sr = decode_audio_bytes(raw, name=name)
        return {"kind": "audio", "audio": audio, "sr": sr}
    if kind == "image":
        return {"kind": "image", "image": decode_image_bytes(raw, name=name)}
    if kind in {"video", "ndarray"}:
        frames, fps = decode_video_bytes(raw, name=name)
        return {"kind": "video", "frames": frames, "fps": fps}
    raise MediaError(PPM_PLAIN_NOT_MEDIA)
