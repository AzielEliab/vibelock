"""Audio/video containers for the existing VibeLock analysis path.

WAV, PNG, PPM, and ``.vlvd`` stay native. Uncompressed PCM inside an
MP4/M4A/MOV ``sowt`` or ``twos`` sample entry is demuxed here.

Compressed containers (MP3, AAC-in-MP4, WebM, MKV, OGG, AVI, and PCM
when the pure demuxer does not recognize the sample entry) are decoded
only when ``ffmpeg`` is on PATH. If it is not, the call fails closed:
no invented waveform, no score.

ffmpeg, when used, is a local subprocess. Bytes are piped on stdin.
Nothing is uploaded.
"""

from __future__ import annotations

import shutil
import struct
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from vibelock.debug import log as dlog
from vibelock.io import (
    MAX_AUDIO_BYTES,
    AudioError,
    decode_audio_bytes,
    sha256_bytes,
    sniff_audio,
)
from vibelock.media import (
    MAX_FRAMES,
    MAX_MEDIA_BYTES,
    MediaError,
    PPM_PLAIN_BROKEN,
    PPM_PLAIN_EMPTY,
    PPM_PLAIN_NOT_MEDIA,
    PPM_PLAIN_TOO_BIG,
    decode_image_bytes,
    decode_ppm,
    decode_video_bytes,
    frames_to_rgb01,
    sniff_media,
)

Array = NDArray[np.float64]

CONTAINER_SUFFIXES = (
    ".mp4",
    ".m4a",
    ".m4v",
    ".mov",
    ".mp3",
    ".aac",
    ".webm",
    ".mkv",
    ".ogg",
    ".oga",
    ".opus",
    ".avi",
    ".flac",
)
_FFMPEG_TIMEOUT_S = 25
_MAX_FFMPEG_OUT = 24 * 1024 * 1024


def ffmpeg_path() -> str | None:
    return shutil.which("ffmpeg")


def ffmpeg_available() -> bool:
    return ffmpeg_path() is not None


def container_suffixes() -> tuple[str, ...]:
    return CONTAINER_SUFFIXES


def _needs_decoder(fmt: str) -> str:
    return (
        f"That file is a {fmt} container. This build cannot decode it "
        "(no ffmpeg on PATH, and it is not uncompressed PCM). "
        "VibeLock will not guess a waveform. Install ffmpeg, or export WAV, PNG, PPM, or .vlvd."
    )


def _empty_decode(fmt: str) -> str:
    return (
        f"VibeLock opened that {fmt} container but found no measurable audio or frames. "
        "Nothing was scored."
    )


def sniff_container(raw: bytes, name: str = "") -> str:
    """Return a format token, or '' if this is not a known container."""
    if not raw:
        return ""
    suffix = Path(name).suffix.lower()
    if len(raw) >= 12 and raw[4:8] == b"ftyp":
        brand = raw[8:12]
        if brand in {b"M4A ", b"M4B "}:
            return "m4a"
        if brand == b"qt  ":
            return "mov"
        return "mp4"
    if len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"AVI ":
        return "avi"
    if raw.startswith(b"OggS"):
        return "ogg"
    if raw.startswith(b"\x1aE\xdf\xa3"):
        if suffix == ".mkv":
            return "mkv"
        return "webm"
    if raw.startswith(b"ID3") or (len(raw) >= 2 and raw[0] == 0xFF and (raw[1] & 0xE0) == 0xE0):
        return "mp3"
    if raw.startswith(b"fLaC"):
        return "flac"
    if suffix in CONTAINER_SUFFIXES:
        return suffix[1:]
    return ""


def _box(tag: bytes, payload: bytes) -> bytes:
    if len(tag) != 4:
        raise ValueError("box tag must be 4 bytes")
    return struct.pack(">I", 8 + len(payload)) + tag + payload


def _walk_boxes(raw: bytes) -> list[tuple[bytes, bytes]]:
    out: list[tuple[bytes, bytes]] = []
    pos = 0
    n = len(raw)
    while pos + 8 <= n:
        size = struct.unpack(">I", raw[pos : pos + 4])[0]
        tag = raw[pos + 4 : pos + 8]
        header = 8
        if size == 1:
            if pos + 16 > n:
                break
            size = struct.unpack(">Q", raw[pos + 8 : pos + 16])[0]
            header = 16
        elif size == 0:
            size = n - pos
        if size < header or pos + size > n:
            break
        out.append((tag, raw[pos + header : pos + size]))
        pos += size
    return out


def _find(boxes: list[tuple[bytes, bytes]], tag: bytes) -> bytes | None:
    for got, payload in boxes:
        if got == tag:
            return payload
    return None


def _parse_mdhd_timescale(mdhd: bytes) -> int:
    if len(mdhd) < 20:
        return 0
    version = mdhd[0]
    if version == 0 and len(mdhd) >= 20:
        return int(struct.unpack(">I", mdhd[12:16])[0])
    if version == 1 and len(mdhd) >= 32:
        return int(struct.unpack(">I", mdhd[20:24])[0])
    return 0


def _audio_entry(stsd_payload: bytes) -> tuple[bytes, int, int] | None:
    """Return (codec, sample_rate, sample_size_bits) from the first stsd entry."""
    if len(stsd_payload) < 16:
        return None
    # version(1)+flags(3)+entry_count(4) then one sample entry box.
    entry_count = struct.unpack(">I", stsd_payload[4:8])[0]
    if entry_count < 1:
        return None
    entry = stsd_payload[8:]
    if len(entry) < 8:
        return None
    size = struct.unpack(">I", entry[:4])[0]
    codec = entry[4:8]
    body = entry[8:size] if size >= 8 and size <= len(entry) else entry[8:]
    # SampleEntry: 6 reserved + 2 data_ref, then QuickTime audio fields.
    if len(body) < 28:
        return None
    sample_size = struct.unpack(">H", body[18:20])[0]
    rate_fixed = struct.unpack(">I", body[24:28])[0]
    rate = int(rate_fixed >> 16)
    return codec, rate, int(sample_size)


def _pcm_from_track(trak: bytes, file_bytes: bytes) -> tuple[Array, int] | None:
    mdia = _find(_walk_boxes(trak), b"mdia")
    if mdia is None:
        return None
    mdia_boxes = _walk_boxes(mdia)
    hdlr = _find(mdia_boxes, b"hdlr")
    if hdlr is None or b"soun" not in hdlr[:32]:
        return None
    mdhd = _find(mdia_boxes, b"mdhd")
    timescale = _parse_mdhd_timescale(mdhd or b"")
    minf = _find(mdia_boxes, b"minf")
    if minf is None:
        return None
    stbl = _find(_walk_boxes(minf), b"stbl")
    if stbl is None:
        return None
    stbl_boxes = _walk_boxes(stbl)
    stsd = _find(stbl_boxes, b"stsd")
    stsz = _find(stbl_boxes, b"stsz")
    if stsd is None or stsz is None:
        return None
    parsed = _audio_entry(stsd)
    if parsed is None:
        return None
    codec, rate, sample_bits = parsed
    if codec not in {b"sowt", b"twos", b"raw ", b"NONE"}:
        return None
    if sample_bits not in {0, 16}:
        return None
    if rate <= 0:
        rate = timescale
    if rate <= 0:
        return None
    if len(stsz) < 12:
        return None
    sample_size, sample_count = struct.unpack(">II", stsz[4:12])
    if sample_size == 0 or sample_count <= 0:
        return None
    co_payload = _find(stbl_boxes, b"co64")
    wide = co_payload is not None
    blob = co_payload if wide else _find(stbl_boxes, b"stco")
    if blob is None or len(blob) < 8:
        return None
    count = struct.unpack(">I", blob[4:8])[0]
    if count < 1:
        return None
    if wide:
        if len(blob) < 16:
            return None
        offset = struct.unpack(">Q", blob[8:16])[0]
    else:
        offset = struct.unpack(">I", blob[8:12])[0]
    nbytes = int(sample_size) * int(sample_count)
    if offset < 0 or offset + nbytes > len(file_bytes):
        return None
    pcm = file_bytes[int(offset) : int(offset) + nbytes]
    if codec == b"sowt":
        samples = np.frombuffer(pcm, dtype="<i2")
    else:
        samples = np.frombuffer(pcm, dtype=">i2")
    audio = samples.astype(np.float64) / 32768.0
    if audio.size == 0:
        return None
    return np.ascontiguousarray(audio), int(rate)


def decode_pcm_mp4(raw: bytes) -> tuple[Array, int] | None:
    """Demux uncompressed 16-bit PCM from an MP4/MOV. None if not that codec."""
    if len(raw) < 16 or raw[4:8] != b"ftyp":
        return None
    boxes = _walk_boxes(raw)
    moov = _find(boxes, b"moov")
    if moov is None:
        return None
    for tag, payload in _walk_boxes(moov):
        if tag != b"trak":
            continue
        got = _pcm_from_track(payload, raw)
        if got is not None:
            return got
    return None


def encode_pcm_mp4(audio: np.ndarray, sr: int) -> bytes:
    """Write a single-track MP4 with little-endian 16-bit PCM (``sowt``)."""
    x = np.asarray(audio, dtype=np.float64).reshape(-1)
    if x.size < 1:
        raise MediaError(PPM_PLAIN_EMPTY)
    if sr <= 0:
        raise MediaError(PPM_PLAIN_BROKEN)
    pcm = np.clip(np.rint(x * 32767.0), -32768, 32767).astype("<i2").tobytes()
    n = x.size
    ftyp = _box(b"ftyp", b"isom" + struct.pack(">I", 0) + b"isom" + b"iso2" + b"mp41")
    mdat_header_len = 8
    data_offset = len(ftyp) + mdat_header_len
    mdat = _box(b"mdat", pcm)

    def mvhd() -> bytes:
        matrix = struct.pack(
            ">9i",
            0x00010000,
            0,
            0,
            0,
            0x00010000,
            0,
            0,
            0,
            0x40000000,
        )
        payload = b"".join(
            [
                struct.pack(">B", 0),
                b"\x00\x00\x00",
                struct.pack(">I", 0),
                struct.pack(">I", 0),
                struct.pack(">I", int(sr)),
                struct.pack(">I", int(n)),
                struct.pack(">I", 0x00010000),
                struct.pack(">H", 0x0100),
                b"\x00" * 10,
                matrix,
                b"\x00" * 24,
                struct.pack(">I", 2),
            ]
        )
        return _box(b"mvhd", payload)

    def tkhd() -> bytes:
        matrix = struct.pack(
            ">9i",
            0x00010000,
            0,
            0,
            0,
            0x00010000,
            0,
            0,
            0,
            0x40000000,
        )
        payload = b"".join(
            [
                struct.pack(">B", 0),
                b"\x00\x00\x00",
                struct.pack(">I", 0),
                struct.pack(">I", 0),
                struct.pack(">I", 1),
                b"\x00" * 4,
                struct.pack(">I", int(n)),
                b"\x00" * 8,
                struct.pack(">h", 0),
                struct.pack(">h", 0),
                struct.pack(">H", 0x0100),
                b"\x00" * 2,
                matrix,
                struct.pack(">I", 0),
                struct.pack(">I", 0),
            ]
        )
        return _box(b"tkhd", payload)

    def mdhd() -> bytes:
        payload = b"".join(
            [
                struct.pack(">B", 0),
                b"\x00\x00\x00",
                struct.pack(">I", 0),
                struct.pack(">I", 0),
                struct.pack(">I", int(sr)),
                struct.pack(">I", int(n)),
                struct.pack(">H", 0x55C4),
                struct.pack(">H", 0),
            ]
        )
        return _box(b"mdhd", payload)

    def hdlr() -> bytes:
        name = b"SoundHandler\x00"
        payload = b"".join(
            [
                struct.pack(">B", 0),
                b"\x00\x00\x00",
                b"\x00\x00\x00\x00",
                b"soun",
                b"\x00" * 12,
                name,
            ]
        )
        return _box(b"hdlr", payload)

    def smhd() -> bytes:
        return _box(b"smhd", struct.pack(">B", 0) + b"\x00\x00\x00" + struct.pack(">HH", 0, 0))

    def dinf() -> bytes:
        url = _box(b"url ", struct.pack(">B", 0) + b"\x00\x00\x01")
        dref = _box(b"dref", struct.pack(">B", 0) + b"\x00\x00\x00" + struct.pack(">I", 1) + url)
        return _box(b"dinf", dref)

    def stsd() -> bytes:
        # 28-byte QuickTime audio sample entry after the box header.
        body = b"".join(
            [
                b"\x00" * 6,
                struct.pack(">H", 1),  # data reference
                struct.pack(">H", 0),  # version
                struct.pack(">H", 0),  # revision
                struct.pack(">I", 0),  # vendor
                struct.pack(">H", 1),  # channels
                struct.pack(">H", 16),  # sample size
                struct.pack(">H", 0),  # compression id
                struct.pack(">H", 0),  # packet size
                struct.pack(">I", int(sr) << 16),
            ]
        )
        entry = _box(b"sowt", body)
        header = struct.pack(">B", 0) + b"\x00\x00\x00" + struct.pack(">I", 1)
        return _box(b"stsd", header + entry)

    def stts() -> bytes:
        payload = struct.pack(">B", 0) + b"\x00\x00\x00" + struct.pack(">III", 1, int(n), 1)
        return _box(b"stts", payload)

    def stsc() -> bytes:
        payload = struct.pack(">B", 0) + b"\x00\x00\x00" + struct.pack(">IIII", 1, 1, int(n), 1)
        return _box(b"stsc", payload)

    def stsz() -> bytes:
        payload = struct.pack(">B", 0) + b"\x00\x00\x00" + struct.pack(">II", 2, int(n))
        return _box(b"stsz", payload)

    def stco() -> bytes:
        payload = struct.pack(">B", 0) + b"\x00\x00\x00" + struct.pack(">II", 1, int(data_offset))
        return _box(b"stco", payload)

    stbl = _box(b"stbl", stsd() + stts() + stsc() + stsz() + stco())
    minf = _box(b"minf", smhd() + dinf() + stbl)
    mdia = _box(b"mdia", mdhd() + hdlr() + minf)
    trak = _box(b"trak", tkhd() + mdia)
    moov = _box(b"moov", mvhd() + trak)
    return ftyp + mdat + moov


def _run_ffmpeg(args: list[str], raw: bytes) -> bytes | None:
    exe = ffmpeg_path()
    if not exe:
        return None
    cmd = [exe, "-hide_banner", "-loglevel", "error", "-nostdin", *args]
    try:
        proc = subprocess.run(
            cmd,
            input=raw,
            capture_output=True,
            timeout=_FFMPEG_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        dlog(f"ffmpeg failed: {exc!r}")
        return None
    if proc.returncode != 0 or not proc.stdout:
        err = proc.stderr.decode("utf-8", "replace")[:240]
        dlog(f"ffmpeg rc={proc.returncode} err={err}")
        return None
    if len(proc.stdout) > _MAX_FFMPEG_OUT:
        raise MediaError(PPM_PLAIN_TOO_BIG)
    return proc.stdout


def _split_ppm_stream(blob: bytes) -> list[Array]:
    """Split concatenated binary P6 frames (ffmpeg image2pipe)."""
    frames: list[Array] = []
    i = 0
    n = len(blob)
    while i + 8 < n and len(frames) < MAX_FRAMES:
        if blob[i : i + 2] != b"P6":
            break
        pos = i + 2
        tokens: list[bytes] = []
        buf = b""
        while pos < n and len(tokens) < 3:
            c = blob[pos : pos + 1]
            if c == b"#":
                while pos < n and blob[pos : pos + 1] not in {b"\n", b"\r"}:
                    pos += 1
                continue
            if c.isspace():
                if buf:
                    tokens.append(buf)
                    buf = b""
                pos += 1
                continue
            buf += c
            pos += 1
        if buf and len(tokens) < 3:
            tokens.append(buf)
        if len(tokens) < 3:
            break
        try:
            w, h, maxv = int(tokens[0]), int(tokens[1]), int(tokens[2])
        except ValueError:
            break
        if w < 1 or h < 1 or maxv <= 0 or maxv > 255:
            break
        need = w * h * 3
        if pos + need > n:
            break
        chunk = blob[i : pos + need]
        try:
            frames.append(decode_ppm(chunk))
        except MediaError:
            break
        i = pos + need
    return frames


def _normalize_pipe_wav(raw: bytes) -> bytes:
    """Rewrite RIFF/data sizes ffmpeg leaves as 0xFFFFFFFF on a pipe."""
    if len(raw) < 44 or raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        return raw
    pos = 12
    while pos + 8 <= len(raw):
        tag = raw[pos : pos + 4]
        size = struct.unpack("<I", raw[pos + 4 : pos + 8])[0]
        if tag == b"data":
            actual = len(raw) - (pos + 8)
            if size > actual:
                raw = raw[: pos + 4] + struct.pack("<I", actual) + raw[pos + 8 :]
            break
        step = 8 + size + (size & 1)
        if size > len(raw) or step <= 0:
            break
        pos += step
    return raw[:4] + struct.pack("<I", max(0, len(raw) - 8)) + raw[8:]


def ffmpeg_decode(raw: bytes) -> dict[str, Any]:
    """Decode audio and a short frame sample with ffmpeg. Raises MediaError if nothing usable."""
    if not ffmpeg_available():
        raise MediaError(_needs_decoder("media"))
    notes: list[str] = []
    audio = None
    sr = 0
    wav = _run_ffmpeg(
        ["-i", "pipe:0", "-vn", "-ac", "1", "-ar", "16000", "-f", "wav", "pipe:1"],
        raw,
    )
    if wav:
        try:
            audio, sr = decode_audio_bytes(_normalize_pipe_wav(wav), name="ffmpeg.wav")
        except AudioError as exc:
            notes.append(str(exc))
            audio = None
    else:
        notes.append("ffmpeg found no audio stream in that container.")
    frames = None
    fps = 0.0
    ppm = _run_ffmpeg(
        [
            "-i",
            "pipe:0",
            "-an",
            "-vf",
            "fps=8,scale=96:96:flags=neighbor",
            "-frames:v",
            "12",
            "-f",
            "image2pipe",
            "-c:v",
            "ppm",
            "pipe:1",
        ],
        raw,
    )
    if ppm:
        got = _split_ppm_stream(ppm)
        if got:
            frames = frames_to_rgb01(np.stack(got, axis=0))
            fps = 8.0
            notes.append(
                "Temporal checks use at most 12 frames sampled at 8 fps by local ffmpeg, "
                "not every source frame. Heuristic, not a full decode of the GOP."
            )
        else:
            notes.append("ffmpeg returned video bytes that were not readable PPM frames.")
    else:
        notes.append("ffmpeg found no video frames in that container.")
    if audio is None and frames is None:
        raise MediaError(_empty_decode("container"))
    return {"audio": audio, "sr": sr, "frames": frames, "fps": fps, "notes": notes, "decoder": "ffmpeg"}


def open_media_bytes(raw: bytes, name: str = "", *, target_sr: int | None = None) -> dict[str, Any]:
    """Decode bytes into audio and/or frames. Fail closed when evidence is missing."""
    if not raw:
        raise MediaError(PPM_PLAIN_EMPTY)
    if len(raw) > max(MAX_MEDIA_BYTES, MAX_AUDIO_BYTES):
        raise MediaError(PPM_PLAIN_TOO_BIG)
    fmt = sniff_container(raw, name) or sniff_audio(raw, name) or sniff_media(raw, name)
    dlog(f"open_media name={name!r} fmt={fmt} n={len(raw)}")
    notes: list[str] = []
    decoder = ""
    audio = None
    sr = 0
    image = None
    frames = None
    fps = 0.0

    native = sniff_media(raw, name)
    if native == "image":
        image = decode_image_bytes(raw, name=name)
        decoder = "image"
        fmt = fmt or "image"
    elif native in {"video", "ndarray"} and sniff_container(raw, name) == "":
        frames, fps = decode_video_bytes(raw, name=name)
        decoder = "vlvd" if raw.startswith(b"VLVD") else "npy"
        fmt = fmt or native
    elif native == "audio" and sniff_container(raw, name) in {"", "mp3", "flac"} and sniff_audio(raw, name) in {
        "wav",
        "flac",
        "mp3",
    }:
        kind = sniff_audio(raw, name)
        try:
            audio, sr = decode_audio_bytes(raw, name=name, target_sr=target_sr)
            decoder = kind or "audio"
            fmt = kind or fmt
        except AudioError:
            if kind == "wav":
                raise
            decoded = None
            if ffmpeg_available():
                decoded = ffmpeg_decode(raw)
            if decoded is None:
                raise MediaError(_needs_decoder(kind or "audio")) from None
            audio = decoded["audio"]
            sr = int(decoded["sr"] or 0)
            frames = decoded["frames"]
            fps = float(decoded["fps"] or 0.0)
            notes.extend(decoded["notes"])
            decoder = "ffmpeg"
            if target_sr and audio is not None and sr and int(target_sr) != sr:
                from vibelock.dsp import resample

                audio = resample(audio, sr, int(target_sr))
                sr = int(target_sr)
    else:
        container = sniff_container(raw, name)
        if not container and native == "":
            raise MediaError(PPM_PLAIN_NOT_MEDIA)
        if container in {"mp4", "m4a", "mov"} or (len(raw) >= 12 and raw[4:8] == b"ftyp"):
            pcm = decode_pcm_mp4(raw)
            if pcm is not None:
                audio, sr = pcm
                decoder = "pcm_mp4"
                fmt = container or "mp4"
                notes.append(
                    "Uncompressed PCM audio was demuxed from the MP4. "
                    "No video frames were read from this sample entry."
                )
        if audio is None and frames is None and image is None:
            if not ffmpeg_available():
                raise MediaError(_needs_decoder(container or fmt or "container"))
            decoded = ffmpeg_decode(raw)
            audio = decoded["audio"]
            sr = int(decoded["sr"] or 0)
            frames = decoded["frames"]
            fps = float(decoded["fps"] or 0.0)
            notes.extend(decoded["notes"])
            decoder = "ffmpeg"
            fmt = container or fmt or "container"
            if target_sr and audio is not None and sr and int(target_sr) != sr:
                from vibelock.dsp import resample

                audio = resample(audio, sr, int(target_sr))
                sr = int(target_sr)
        elif target_sr and audio is not None and sr and int(target_sr) != sr:
            from vibelock.dsp import resample

            audio = resample(audio, sr, int(target_sr))
            sr = int(target_sr)

    if audio is None and image is None and frames is None:
        raise MediaError(_empty_decode(fmt or "media"))

    if frames is not None and image is None and int(frames.shape[0]) == 1:
        image = frames[0]
    kind = "audio"
    if frames is not None and audio is not None:
        kind = "av"
    elif frames is not None:
        kind = "video"
    elif image is not None and audio is not None:
        kind = "av"
    elif image is not None:
        kind = "image"
    return {
        "kind": kind,
        "audio": audio,
        "sr": int(sr or 0),
        "image": image,
        "frames": frames,
        "fps": float(fps or 0.0),
        "format": fmt or kind,
        "decoder": decoder or "unknown",
        "notes": notes,
        "sha256": sha256_bytes(raw),
        "n_bytes": len(raw),
        "filename": Path(name).name if name else "",
    }


def load_media_path(
    path: str | Path,
    *,
    target_sr: int | None = None,
    fps: float | None = None,
) -> dict[str, Any]:
    """Load a file or a folder of stills. Same dict shape as ``open_media_bytes``."""
    path = Path(path)
    if path.is_dir():
        from vibelock.media import load_video

        frames, rate, meta = load_video(path, fps=fps)
        return {
            "kind": "video",
            "audio": None,
            "sr": 0,
            "image": None,
            "frames": frames,
            "fps": rate,
            "format": "frames",
            "decoder": "stills",
            "notes": [],
            "sha256": meta.get("sha256"),
            "n_bytes": meta.get("n_bytes"),
            "filename": meta.get("filename") or path.name,
            "meta": meta,
        }
    if not path.is_file():
        raise FileNotFoundError(f"Media file not found: {path}")
    raw = path.read_bytes()
    if len(raw) > max(MAX_MEDIA_BYTES, MAX_AUDIO_BYTES):
        raise MediaError(PPM_PLAIN_TOO_BIG)
    opened = open_media_bytes(raw, name=path.name, target_sr=target_sr)
    if fps and opened.get("frames") is not None and opened.get("decoder") == "stills":
        opened["fps"] = float(fps)
    opened["filename"] = path.name
    opened["meta"] = {
        "path": str(path),
        "filename": path.name,
        "sha256": opened.get("sha256"),
        "n_bytes": opened.get("n_bytes"),
        "format": opened.get("format"),
        "decoder": opened.get("decoder"),
        "kind": opened.get("kind"),
    }
    return opened
