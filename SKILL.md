---
name: VibeLock
description: Use when calling VibeLock hosted /v1 or installing the local package for physics + A/V deepfake detection. Author Aziel Eliab.
---

# VibeLock

Physics + A/V deepfake detection. Risk assessment, not courtroom proof. Author: **Aziel Eliab**.

**THIS IS:** a multi-signal detector — vocal-tract / vibration physics, spatial image artifacts, temporal video flicker/flow, unnatural pitch/phase shifts, and talking-head A/V sync (local CLI + hosted advisory `/v1/analyze` and `/v1/detect`).

**THIS IS NOT:** courtroom proof, a liveness detector, a live microphone, face recognition, or a claim that physics cannot be forged. Hosted `/v1` does not increment downloads or views.

Always send `User-Agent: Mozilla/5.0`. Cloudflare Workers may 403 an empty agent.

The Worker homepage is a full product UI (title `VibeLock — Aziel Eliab`):
in-browser analyze against `/v1/analyze`, plus counted download and
one-click install. https://vibelock-download-tracker.vibelock.workers.dev/

## Call these URLs

- Worker OpenAPI: https://vibelock-download-tracker.vibelock.workers.dev/openapi.json
- Catalog OpenAPI: https://aziel-runtime.vibelock.workers.dev/openapi.json
- MCP: `POST https://aziel-runtime.vibelock.workers.dev/mcp`
- Live skill (this markdown): `GET https://vibelock-download-tracker.vibelock.workers.dev/v1/skill`

Ops (do **not** increment downloads or views):

- `GET /v1/health` — liveness
- `GET /v1/skill` — this file
- `POST /v1/analyze` — advisory score from audio features/PCM and/or visual/pitch/A/V features
- `POST /v1/detect` — same engine, deepfake-oriented request body

Grok: import OpenAPI as a custom tool. ChatGPT: GPT Actions. Venice: HTTP tools.

## Example

```bash
curl -s -A 'Mozilla/5.0' https://vibelock-download-tracker.vibelock.workers.dev/v1/health
curl -s -A 'Mozilla/5.0' https://vibelock-download-tracker.vibelock.workers.dev/v1/skill
curl -s -A 'Mozilla/5.0' -X POST https://vibelock-download-tracker.vibelock.workers.dev/v1/detect \
  -H 'content-type: application/json' \
  -d '{"features":{"rms":0.08,"zcr":0.07},"visual":{"blockiness":1.8,"noise_cv":0.7},"pitch":{"f0_jump":8.5}}'
```

## Local (after one-click install)

```bash
curl -fsSL https://vibelock-download-tracker.vibelock.workers.dev/install.sh | bash
vibelock ui
vibelock doctor
vibelock detect path/to/media.png
```

Then open http://127.0.0.1:8760 (loopback only). WAV, PNG, PPM, `.vlvd` frame stacks.

Counted download (gzip HTTP 200, no 302): https://vibelock-download-tracker.vibelock.workers.dev/download?asset=vibelock-0.3.0.tar.gz
GitHub: https://github.com/AzielEliab/vibelock

Paper: DOI https://doi.org/10.5281/zenodo.21431610 · https://zenodo.org/records/21431610 · Apache-2.0. Forks welcome.
