# Contributing to VibeLock

**Forks are first-class.** This project is Apache-2.0; you do not need
permission to fork, patch, or redistribute. Pull requests are welcome
if you want a change upstream. Keep a fork forever if you do not.

**Forks are welcome and always allowed.**

## How to run tests

```bash
pip install -e ".[dev]"
python -m pytest -q
```

Python 3.10+, numpy, scipy, pytest. No hardware. Fixtures in
`tests/conftest.py` are synthetic (seeds in `tests/helpers.py`).

## Ground rules

1. Treat `origin` as one peer among many. Downstream forks are part of
   the download-tracking model (see `workers/download-tracker`): they
   report as `{owner}/{repo}`, not as anonymous noise.
2. **Do not pretend the transfer-function baseline is a human dataset.**
   It is generated in `vibelock.synth`. If you replace it with recorded
   contact-mic data, document the corpus, the consent, and the license
   in the same breath as the code change.
3. **No STT, no identity, no silent retention of raw audio.** Privacy
   constraints in `docs/whitepaper.md` are part of the design.
4. **Keep the DSP dependency-light.** numpy + scipy. Do not pull a
   machine-learning stack into the core CLI.
5. **Do not invent evaluation numbers or fake citations.** Thresholds
   are engineering defaults. If you measure something on a real set,
   say so, with the set’s name and license.
6. **Do not gut the DSP to make a test pass.** If a threshold is too
   tight, loosen the test.
7. **Suite mesh is a proxy, not a local op.** `/v1/mesh/*` PROXY to
   aziel-runtime via `AZIEL_RUNTIME`. Default OFF. QNM rollup is
   live|locked|isolated only. QNS-CD-1.0 is a hub cite / Worker mesh
   cross-map only (`qns_cd` in `mesh.js`) — do not implement qnsd here
   and do not add a public qnsd proxy. No Node Gate. No auto-heal.
   Not anonymity.

## Where to change things

- Dual-channel checks: `vibelock/dual_channel.py`
- Audio-only checks: `vibelock/forensic.py`
- Pitch / phase-shift: `vibelock/pitch.py`
- Spatial image: `vibelock/vision.py`
- Temporal video: `vibelock/temporal.py`
- Talking-head sync: `vibelock/avsync.py`
- Image/video I/O: `vibelock/media.py`
- Shared DSP: `vibelock/dsp.py`
- Reason codes / scoring: `vibelock/scoring.py`
- New checks need a synthetic fixture that moves the score in the
  documented direction (authentic higher, attacked lower).
- Suite mesh / QNM Live Nodes / QNS-CD-1.0 cross-map:
  `workers/download-tracker/src/mesh.js`
  (`/v1/mesh/*` PROXY to aziel-runtime; `QNS_CD` hub cite only).

## Reporting downloads from a fork

Point users at GitHub Releases. If you cut your own releases, POST
`/event` on the download-tracker worker so counts stay attributed to
your `owner/repo` (see `workers/download-tracker/README.md`). The
worker at `https://downloads.vibelock.dev` must be deployed first.

## License of contributions

By submitting a change you agree it is licensed under Apache-2.0, the
same license as the rest of the tree. Keep the copyright lines honest.
