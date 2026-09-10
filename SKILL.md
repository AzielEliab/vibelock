---
name: VibeLock
description: Use when calling VibeLock hosted /v1 or installing the local package for physics + A/V deepfake detection. This Worker /v1/mesh/* PROXY to aziel-runtime via AZIEL_RUNTIME. Suite mesh default OFF. QNM-BUILD-1.0 live|locked|isolated. QNS-CD-1.0 photon QNS1 packet transfer is a hub cite / Worker mesh cross-map only (not Softwares-tab; no public qnsd proxy). No Node Gate. No auto-heal. Not anonymity. Author Aziel Eliab.
---

# VibeLock

Physics + A/V deepfake detection. Risk assessment, not courtroom proof. Author: **Aziel Eliab**.

**THIS IS:** a multi-signal detector — vocal-tract / vibration physics, spatial image artifacts, temporal video flicker/flow, unnatural pitch/phase shifts, and talking-head A/V sync (local CLI + hosted advisory `/v1/analyze` and `/v1/detect`).

**THIS IS NOT:** courtroom proof, a liveness detector, a live microphone, face recognition, or a claim that physics cannot be forged. Hosted `/v1` does not increment downloads or views.

Always send `User-Agent: Mozilla/5.0`. Cloudflare Workers may 403 an empty agent.

The Worker homepage is a full product UI (title `VibeLock — Aziel Eliab`):
in-browser analyze against `/v1/analyze`, plus counted download,
one-click install, and the suite Live Nodes strip (`GET /v1/mesh`).
https://vibelock-download-tracker.vibelock.workers.dev/

## Call these URLs

- Worker OpenAPI: https://vibelock-download-tracker.vibelock.workers.dev/openapi.json
- Catalog OpenAPI: https://aziel-runtime.vibelock.workers.dev/openapi.json
- MCP: `POST https://aziel-runtime.vibelock.workers.dev/mcp`
- This Worker MCP pointer: `GET https://vibelock-download-tracker.vibelock.workers.dev/mcp`
- Live skill (this markdown): `GET https://vibelock-download-tracker.vibelock.workers.dev/v1/skill`
- Suite mesh: `GET https://vibelock-download-tracker.vibelock.workers.dev/v1/mesh` (PROXY; default OFF; QNS-CD-1.0 cross-map on the Live Nodes payload)

Ops (do **not** increment downloads or views):

- `GET /v1/health` — liveness
- `GET /v1/skill` — this file
- `POST /v1/analyze` — advisory score from audio features/PCM and/or visual/pitch/A/V features
- `POST /v1/detect` — same engine, deepfake-oriented request body
- `GET /v1/mesh` — PROXY suite mesh status. Default OFF. QNM live|locked|isolated. QNS-CD-1.0 photon QNS1 packet transfer is stamped as a hub cite / Worker mesh cross-map (`qns_cd`). Never enables. No Node Gate. No auto-heal. No public qnsd proxy.
- `GET /v1/mesh/nodes` — PROXY Live Nodes roster (5-minute presence). Same QNS-CD-1.0 cross-map.
- `POST /v1/mesh/{enable,disable,join,heartbeat,leave,broadcast}` — PROXY. Bearer required to enable. Not AnonBroadcast. Not qnsd.
- `GET /mcp` — OpenAPI/MCP pointer (catalog MCP + FragGate `slug=mesh`). Not a second MCP.

QNS-CD-1.0 is **not** a Softwares-tab product. Local qnsd is coded in [qnm-node](https://github.com/AzielEliab/qnm-node). Runtime cites + catalog field live in [aziel-runtime](https://github.com/AzielEliab/aziel-runtime). Pair custody is [AZInterface](https://github.com/AzielEliab/azinterface). This Worker only cites the cross-map on mesh status / Live Nodes.

Works with ChatGPT (GPT Actions / OpenAI), Grok (xAI), Venice, Claude (Anthropic), Cursor (MCP), Glama (MCP), Perplexity, Microsoft Copilot / Bing, Google Gemini / Vertex, Mistral, Meta AI, Apple Intelligence surfaces, Amazon Q tooling, DuckAssist, You.com, Cohere, and other MCP/OpenAPI-capable assistants.

Import OpenAPI as a custom tool (ChatGPT: GPT Actions; Grok/xAI: HTTP/OpenAPI tool; Venice: HTTP tools). MCP clients (Cursor, Glama, and others): POST the catalog. Catalog MCP `mesh_*` + FragGate `slug=mesh`. No per-crawler install packages.

## Example

```bash
curl -s -A 'Mozilla/5.0' https://vibelock-download-tracker.vibelock.workers.dev/v1/health
curl -s -A 'Mozilla/5.0' https://vibelock-download-tracker.vibelock.workers.dev/v1/skill
curl -s -A 'Mozilla/5.0' https://vibelock-download-tracker.vibelock.workers.dev/v1/mesh
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
