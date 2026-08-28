# VibeLock

Physical-consistency evaluation of speech audio.

**Author:** Aziel Eliab  
**Date:** July 2026  
**License:** [Apache-2.0](LICENSE)

> Sound can be forged. Physics is harder to fake.

VibeLock asks whether a recording is physically consistent with human
vocal vibration and biomechanical resonance. It is local DSP, not a
cloud model and not a speech-to-text pipeline.

Two modes:

1. **Dual-channel** — air microphone plus body-coupled vibration (jaw
   accelerometer, contact mic, or IMU). Sync, drift-correct, then test
   coherence, the vibration-to-air transfer function, latency, and
   resonance decay.
2. **Audio-only forensic** — when vibration is absent. Spectral
   smoothness, phase continuity, formant stability, decay, splices,
   vocoder buzz. This is a **risk assessment, not a proof of liveness.**

Output: a score in `[0, 1]` and machine-readable reason codes
(`COHERENCE_LOW`, `PHASE_DISCONTINUITY`, `TRANSFER_RESIDUAL_HIGH`,
`DECAY_IMPLAUSIBLE`, `FORMANT_UNSTABLE`, `TEMPORAL_SPLICE`, …).

The transfer-function baseline is learned from **synthetic
physically-plausible pairs**, not from a published human dataset. That
is documented in `vibelock/synth.py` and `docs/whitepaper.md`.

Privacy: no STT, no identity, raw audio is not retained by default.
Processing is local.

**Forks are welcome and always allowed.**

---

## Download

**Get release builds here:**

# → [https://github.com/AzielEliab/vibelock/releases](https://github.com/AzielEliab/vibelock/releases) ←

Counted downloads (canonical tree, branches, and forks) are tracked by
the Cloudflare Worker:

- Tracker: [https://downloads.vibelock.dev](https://downloads.vibelock.dev)
- Stats JSON: [https://downloads.vibelock.dev/stats](https://downloads.vibelock.dev/stats)

Prefer a tracked asset URL so branch and fork dimensions are recorded:

```
https://downloads.vibelock.dev/download/AzielEliab/vibelock/latest/vibelock-0.1.0.tar.gz
```

Forks identified by GitHub `owner/repo` can POST `/event` — see
`workers/download-tracker/README.md`. Source stays this repository;
the worker only counts.

---

## Install

Python 3.10+ . numpy and scipy only (no ML stack).

```bash
python -m pip install -e ".[dev]"
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
python examples/synthetic_pair.py
```

That script writes a physically-plausible dual-channel pair and runs
`vibelock analyze` on it.

## Tests

```bash
cd /workspace/vibelock   # or the clone root
python -m pip install -e ".[dev]"
pytest -q
```

Fixtures are synthetic. They prove each physical check moves the score
the right way.

## Layout

```
vibelock/           library (dsp, dual_channel, forensic, scoring, io, cli)
tests/              pytest, synthetic attacks
docs/whitepaper.md  July 2026 spec
examples/           generate a pair and analyze it
workers/download-tracker/   Cloudflare Worker + wrangler.toml
```

## License

Apache-2.0. See [LICENSE](LICENSE).

Forks are welcome and always allowed.
