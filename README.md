# VibeLock

Physics + A/V deepfake detection.

**Author:** Aziel Eliab
**Date:** September 2026 (speech physics: July 2026)
**License:** [Apache-2.0](LICENSE)

> Sound can be forged. Pixels can be forged. Physics is harder to fake.


## One-click install

```bash
curl -fsSL https://vibelock-download-tracker.vibelock.workers.dev/install.sh | bash
```

The script curls the **counted** tarball from this project's Worker
(`/download`, User-Agent `Mozilla/5.0`), extracts, makes a venv, and
`pip install -e .`. Then run `vibelock ui`.

Or tap **Download** / **One-click install** on the Worker homepage
(a 6th-grader can tap it):
https://vibelock-download-tracker.vibelock.workers.dev/

## Counted download (Cloudflare Worker)

**This is the counted download.** GitHub releases exist as a mirror.
The Worker serves the gzip itself (HTTP 200, no 302 to GitHub).

# → [https://vibelock-download-tracker.vibelock.workers.dev/](https://vibelock-download-tracker.vibelock.workers.dev/) ←

Direct tarball (also counted):
[vibelock-0.3.0.tar.gz](https://vibelock-download-tracker.vibelock.workers.dev/download?asset=vibelock-0.3.0.tar.gz)

- Live count JSON: [https://vibelock-download-tracker.vibelock.workers.dev/stats](https://vibelock-download-tracker.vibelock.workers.dev/stats)
- OpenAPI: [https://vibelock-download-tracker.vibelock.workers.dev/openapi.json](https://vibelock-download-tracker.vibelock.workers.dev/openapi.json)
- Skill: [https://vibelock-download-tracker.vibelock.workers.dev/v1/skill](https://vibelock-download-tracker.vibelock.workers.dev/v1/skill)
- One-click install: [https://vibelock-download-tracker.vibelock.workers.dev/install.sh](https://vibelock-download-tracker.vibelock.workers.dev/install.sh)
- GitHub: [https://github.com/AzielEliab/vibelock](https://github.com/AzielEliab/vibelock)

- DOI: [10.5281/zenodo.21431610](https://doi.org/10.5281/zenodo.21431610)
- Zenodo: [https://zenodo.org/records/21431610](https://zenodo.org/records/21431610)

Isolated counter: Worker `vibelock-download-tracker`, KV `VIBELOCK_DOWNLOADS`. Not mixed with any other product. `/v1` does not increment downloads.


## Quick start

1. Install: `python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`
2. Open the local UI: `vibelock ui`
3. In the browser at http://127.0.0.1:8760, tap **Add file** (WAV / PNG / PPM / `.vlvd`; FLAC/MP3 if this build can read them), then **Export JSON report**. Optional check: `vibelock doctor --verify`.

Loopback only (`127.0.0.1`). No CDN, no telemetry. This is a **media authenticity advisory, not courtroom proof.**

Counted download: [https://vibelock-download-tracker.vibelock.workers.dev/](https://vibelock-download-tracker.vibelock.workers.dev/)

Optional mic gate (YOUR default input only; extra `[tether]`):

```bash
pip install -e ".[tether]"
vibelock listen --gate
```


VibeLock asks whether media is physically consistent with a real vocal
tract, a real camera exposure, and — when both are present — a mouth
that produced the waveform. It is local DSP (numpy + scipy): vibration–
audio coherence, spatial/temporal image-video artifacts, and unnatural
pitch/phase shifts. Not a cloud model and not a speech-to-text pipeline.

See the spec: [docs/whitepaper.md](docs/whitepaper.md).
How to contribute: [CONTRIBUTING.md](CONTRIBUTING.md).

**Forks are welcome and always allowed.**


---

## Download

**Counted download page (this project only, ticks automatically):**

# → [https://vibelock-download-tracker.vibelock.workers.dev/](https://vibelock-download-tracker.vibelock.workers.dev/) ←

The big button on that page is the download. The number next to it is
**vibelock only** — its own Worker and KV, not mixed with VibeLock or
anything else. Clicking it increments the counter. Nobody reports
anything. Forks that use the same link are counted too.

Direct tarball (also counted): [vibelock-0.3.0.tar.gz](https://vibelock-download-tracker.vibelock.workers.dev/download?asset=vibelock-0.3.0.tar.gz)

- Live count JSON: [https://vibelock-download-tracker.vibelock.workers.dev/count](https://vibelock-download-tracker.vibelock.workers.dev/count)
- Stats: [https://vibelock-download-tracker.vibelock.workers.dev/stats](https://vibelock-download-tracker.vibelock.workers.dev/stats)
- GitHub releases: [https://github.com/AzielEliab/vibelock/releases](https://github.com/AzielEliab/vibelock/releases)

---

## iPhone & Android

A local-first Flutter client lives in [`mobile/`](mobile/). Open that
folder in Android Studio or Xcode through Flutter (`flutter create .`
first if `android/` / `ios/` still hold the skeleton READMEs). Record
from the mic; energy / ZCR heuristics labeled as a **risk assessment,
not a liveness proof**.

Counted desktop download: [https://vibelock-download-tracker.vibelock.workers.dev/](https://vibelock-download-tracker.vibelock.workers.dev/)

Forks are welcome and always allowed.

---

## Signals

1. **Dual-channel physics** — air microphone plus body-coupled vibration
   (jaw accelerometer, contact mic, or IMU). Sync, drift-correct, then
   test coherence, the vibration-to-air transfer function, latency, and
   resonance decay. This is the strong physical test.
2. **Audio-only forensic + pitch/phase** — spectral smoothness, Hilbert
   phase, formant stability, decay, splices, vocoder buzz, F0 jumps,
   robotic flat pitch, phase-vocoder stretch. A **risk assessment, not
   a proof of liveness.**
3. **Spatial image artifacts** — generator upsampling lattice (2-D FFT),
   PRNU-like noise mismatch, 8×8 block energy, local illuminant drift,
   blend seams, shading roughness.
4. **Temporal video artifacts** — flicker, block-matching flow, identity
   histogram jumps on still pairs, frame-interpolation ghosts, lighting
   drift.
5. **Talking-head A/V sync** — audio RMS envelope vs center-crop motion
   energy and envelope GCC-PHAT delay.

Output: a score in `[0, 1]`, a verdict (`consistent` / `deepfake` /
`inconclusive` / `inconsistent`), and machine-readable reason codes
(`COHERENCE_LOW`, `FREQ_FINGERPRINT`, `PITCH_JUMP`, `AV_SYNC_FAIL`,
`TEMPORAL_FLICKER`, `BLEND_BOUNDARY`, …).

The transfer-function baseline is learned from **synthetic
physically-plausible pairs**, not from a published human dataset. Visual
fixtures are also synthetic cartoons (`vibelock/synth_media.py`). This
README does not invent evaluation numbers.

Privacy: no STT, no identity, no face recognition. Raw media is not
retained by default. Processing is local.

## Install

Python 3.10+. numpy and scipy only (no ML stack).

```bash
pip install -e ".[dev]"
```

From a release artifact:

```bash
python -m pip install vibelock-0.3.0.tar.gz
```

## CLI

```bash
# Audio-only forensic (risk assessment)
vibelock analyze path/to/air.wav

# Dual-channel: air + body-coupled vibration
vibelock analyze path/to/air.wav --vibration path/to/jaw.wav

# Image / video / talking-head (detect is an alias)
vibelock detect path/to/face.png
vibelock detect path/to/frames/ --fps 25
vibelock detect path/to/air.wav --video path/to/frames/

# JSON (score + verdict + reason codes + per-check metrics)
vibelock analyze path/to/air.wav --vibration path/to/jaw.wav --json

# Resample both channels first
vibelock analyze path/to/air.wav --vibration path/to/jaw.wav --sr 16000

vibelock version
vibelock doctor --verify   # local health + WAV/PNG + vision direction
vibelock ui                # localhost UI on 127.0.0.1:8760
```

`--verify` on `analyze` re-reads the file and confirms the score and SHA-256 match.
`--export PATH` writes a JSON report (hashes, scores, limitation).

## Local UI

Local UI: `pip install -e . && vibelock ui` then open http://127.0.0.1:8760

Binds to `127.0.0.1` only. Self-contained HTML (no CDN, no tracking, no telemetry). Giant **Add file** (WAV / PNG / PPM / `.vlvd`, plus FLAC/MP3 when a decoder is present), **Sample tone**, **Sample photo**, **Sample deepfake**, **Export JSON report** (hashes, scores, limitation). **Simple** view: one score and kid-plain *consistent* / *inconsistent*. **Advanced** view: hashes and per-check codes. Hard max size; truncated or foreign files are rejected in plain language without crashing.

```bash
vibelock ui --host 127.0.0.1 --port 8760
```

`analyze` exits 0 when the run completes, including low scores. A
nonzero exit means the file could not be read or the arguments were
wrong.

Library entry point:

```python
from vibelock import analyze
from vibelock.io import load_audio
from vibelock.media import load_image, load_video

audio, sr = load_audio("air.wav")
vib, _ = load_audio("jaw.wav", target_sr=sr)
print(analyze(audio, sr, vibration=vib).score)

img, _ = load_image("face.png")
print(analyze(image=img).verdict, analyze(image=img).reason_codes)

frames, fps, _ = load_video("frames/")
print(analyze(audio, sr, frames=frames, fps=fps).verdict)
```

## Synthetic example

No hardware required:

```bash
python examples/analyze_synthetic.py
```

That script generates a physically-plausible dual-channel pair with
`vibelock.synth.make_pair`, writes WAVs, runs `analyze`, and prints
the score and reason codes.

A/V cartoons (no hardware):

```bash
python examples/analyze_deepfake.py
```

## Tests

```bash
pip install -e ".[dev]"
python -m pytest -q
```

Fixtures in `tests/conftest.py` are synthetic. They prove each physical
check moves the score the right way (authentic higher than attacked).

## Layout

```
vibelock/           library (dsp, forensic, vision, temporal, pitch, avsync, media)
tests/              pytest, synthetic audio + A/V attacks
docs/whitepaper.md  July 2026 spec + September 2026 A/V engine
examples/           generate a pair / deepfake cartoon and analyze it
workers/download-tracker/   Cloudflare Worker + wrangler.toml
mobile/             Flutter iPhone & Android client
CONTRIBUTING.md     forks are first-class
```

## Use with Grok, ChatGPT, Venice

Live HTTPS runtime on the download-tracker Worker (does **not** increment the download counter):

- OpenAPI 3.1: https://vibelock-download-tracker.vibelock.workers.dev/openapi.json
- Health: https://vibelock-download-tracker.vibelock.workers.dev/v1/health
- How to wire tools: https://vibelock-download-tracker.vibelock.workers.dev/ai
- MCP catalog: https://aziel-runtime.vibelock.workers.dev/mcp

POST `/v1/analyze` or `/v1/detect` with `features:{rms,zcr,...}`, limited
`pcm_b64`+rate, and/or `visual` / `pitch` / `av` feature objects.
**Risk assessment, not a liveness proof.** Hosted is not a live mic;
desktop `listen` stays local. The Worker ports the same heuristics in JS.

**ChatGPT Actions:** GPT Editor → Actions → Import from URL → `https://vibelock-download-tracker.vibelock.workers.dev/openapi.json` (no auth).

**Grok / xAI tools:** add an HTTP/OpenAPI tool pointing at `https://vibelock-download-tracker.vibelock.workers.dev/openapi.json`.

**Venice HTTP tools:** add an HTTP tool with method, URL, and JSON body from that spec. Start with GET `https://vibelock-download-tracker.vibelock.workers.dev/v1/health`.

```bash
curl -sS -A 'Mozilla/5.0' -X POST https://vibelock-download-tracker.vibelock.workers.dev/v1/detect \
  -H 'content-type: application/json' \
  -d '{"features":{"rms":0.08,"zcr":0.07},"visual":{"blockiness":1.8,"noise_cv":0.7},"pitch":{"f0_jump":8.5}}'
```

GET `/download` still serves the gzip tarball and is counted.


## License

Apache-2.0. See [LICENSE](LICENSE).

Forks are welcome and always allowed.
