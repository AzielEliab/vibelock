# VibeLock

Physical-consistency evaluation of speech audio.

**Author:** Aziel Eliab
**Date:** July 2026
**License:** [Apache-2.0](LICENSE)

> Sound can be forged. Physics is harder to fake.

VibeLock asks whether a recording is physically consistent with human
vocal vibration and biomechanical resonance. It is local DSP (numpy +
scipy), not a cloud model and not a speech-to-text pipeline.

See the spec: [docs/whitepaper.md](docs/whitepaper.md).
How to contribute: [CONTRIBUTING.md](CONTRIBUTING.md).

**Forks are welcome and always allowed.**

---

## Download

**Release builds (canonical):**

# → [https://github.com/AzielEliab/vibelock/releases](https://github.com/AzielEliab/vibelock/releases) ←

**Tracked download endpoint (Cloudflare Worker placeholder):**

- Worker: [https://downloads.vibelock.dev](https://downloads.vibelock.dev)
- Stats: [https://downloads.vibelock.dev/stats](https://downloads.vibelock.dev/stats)

The worker **must be deployed** before those URLs work. Until then, use
the GitHub Releases link above. Source, wrangler config, and deploy
steps live in [`workers/download-tracker/`](workers/download-tracker/).

Tracked asset URL (after deploy):

```
https://downloads.vibelock.dev/download?repo=AzielEliab/vibelock&tag=latest&asset=vibelock-0.1.0.tar.gz
```

Query params: `owner`, `repo` (`owner/repo` is accepted), `branch`,
`fork` (`1` or `owner/repo`), `tag`, `asset`. Forks can POST `/event`
so their downloads are counted separately. See the worker README.

---

## Dual-channel vs audio-only

1. **Dual-channel** — air microphone plus body-coupled vibration (jaw
   accelerometer, contact mic, or IMU). Sync, drift-correct, then test
   coherence, the vibration-to-air transfer function, latency, and
   resonance decay. This is the strong physical test.
2. **Audio-only forensic** — when vibration is absent. Spectral
   smoothness, phase continuity, formant stability, decay, splices,
   vocoder buzz. This is a **risk assessment, not a proof of liveness.**

Output: a score in `[0, 1]` and machine-readable reason codes
(`COHERENCE_LOW`, `LATENCY_OUT_OF_BOUNDS`, `PHASE_DISCONTINUITY`,
`TRANSFER_RESIDUAL_HIGH`, `DECAY_IMPLAUSIBLE`, `FORMANT_UNSTABLE`,
`TEMPORAL_SPLICE`, `VOCODER_BUZZ`, …).

The transfer-function baseline is learned from **synthetic
physically-plausible pairs**, not from a published human dataset. That
is documented in `vibelock/synth.py` and `docs/whitepaper.md`. This
README does not invent evaluation numbers.

Privacy: no STT, no identity, raw audio is not retained by default.
Processing is local.

## Install

Python 3.10+. numpy and scipy only (no ML stack).

```bash
pip install -e ".[dev]"
```

From a release artifact:

```bash
python -m pip install vibelock-0.1.0.tar.gz
```

## CLI

```bash
# Audio-only forensic (risk assessment)
vibelock analyze path/to/air.wav

# Dual-channel: air + body-coupled vibration
vibelock analyze path/to/air.wav --vibration path/to/jaw.wav

# JSON (score + reason codes + per-check metrics)
vibelock analyze path/to/air.wav --vibration path/to/jaw.wav --json

# Resample both channels first
vibelock analyze path/to/air.wav --vibration path/to/jaw.wav --sr 16000

vibelock version
```

`analyze` exits 0 when the run completes, including low scores. A
nonzero exit means the file could not be read or the arguments were
wrong.

Library entry point:

```python
from vibelock import analyze
from vibelock.io import load_audio

audio, sr = load_audio("air.wav")
vib, _ = load_audio("jaw.wav", target_sr=sr)
result = analyze(audio, sr, vibration=vib)
print(result.score, result.reason_codes)
```

## Synthetic example

No hardware required:

```bash
python examples/analyze_synthetic.py
```

That script generates a physically-plausible dual-channel pair with
`vibelock.synth.make_pair`, writes WAVs, runs `analyze`, and prints
the score and reason codes.

## Tests

```bash
pip install -e ".[dev]"
python -m pytest -q
```

Fixtures in `tests/conftest.py` are synthetic. They prove each physical
check moves the score the right way (authentic higher than attacked).

## Layout

```
vibelock/           library (dsp, dual_channel, forensic, scoring, io, cli)
tests/              pytest, synthetic attacks
docs/whitepaper.md  July 2026 spec
examples/           generate a pair and analyze it
workers/download-tracker/   Cloudflare Worker + wrangler.toml
CONTRIBUTING.md     forks are first-class
```

## License

Apache-2.0. See [LICENSE](LICENSE).

Forks are welcome and always allowed.
