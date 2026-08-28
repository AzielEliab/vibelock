# Contributing to VibeLock

Forks are first-class. This project is Apache-2.0; you do not need
permission to fork, patch, or redistribute. Send a pull request if you
want the change upstream. Keep a fork forever if you do not.

## Ground rules

1. **Forks are welcome and always allowed.** Treat `origin` as one
   peer among many. Downstream forks are part of the download-tracking
   model (see `workers/download-tracker`): they report as
   `{owner}/{repo}`, not as anonymous noise.
2. **Do not pretend the transfer-function baseline is a human dataset.**
   It is generated in `vibelock.synth`. If you replace it with recorded
   contact-mic data, document the corpus, the consent, and the license
   in the same breath as the code change.
3. **No STT, no identity, no silent retention of raw audio.** Privacy
   constraints in `docs/whitepaper.md` §6 are part of the design, not
   optional flavor.
4. **Keep the DSP dependency-light.** numpy + scipy. Do not pull a
   machine-learning stack to “improve the score” unless you are adding
   an explicitly optional extra that the core CLI does not import.
5. **Do not invent evaluation numbers or fake citations.** Thresholds
   are engineering defaults. If you measure something on a real set,
   say so, with the set’s name and license.

## How to work

```bash
python -m pip install -e ".[dev]"
pytest -q
```

- Dual-channel checks live in `vibelock/dual_channel.py`.
- Audio-only checks live in `vibelock/forensic.py`.
- Shared DSP lives in `vibelock/dsp.py`.
- Reason codes live in `vibelock/scoring.py`.
- Every new check needs a synthetic fixture in `tests/` that moves the
  score in the documented direction (authentic higher, attacked lower,
  and the reason code present on the attack).

## Reporting downloads from a fork

Point users at GitHub Releases. If you cut your own releases, POST
`/event` on the download-tracker worker so counts stay attributed to
your `owner/repo` (see `workers/download-tracker/README.md`).

## License of contributions

By submitting a change you agree it is licensed under Apache-2.0, the
same license as the rest of the tree. Keep the copyright lines honest.
