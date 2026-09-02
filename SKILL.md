---
name: VibeLock
description: Use when calling VibeLock hosted /v1 or installing the local package. Author Aziel Eliab.
---

# VibeLock

Physical-consistency evaluation of speech. Risk assessment, not a liveness proof. Author: **Aziel Eliab**.

**THIS IS:** physical-consistency evaluation of speech audio (local CLI + hosted advisory /v1/analyze).

**THIS IS NOT:** courtroom audio proof, a liveness detector, a live microphone, or a claim that physics cannot be forged. Hosted `/v1` does not increment downloads or views.

Always send `User-Agent: Mozilla/5.0`. Cloudflare Workers may 403 an empty agent.

## Call these URLs

- Worker OpenAPI: https://vibelock-download-tracker.vibelock.workers.dev/openapi.json
- Catalog OpenAPI: https://aziel-runtime.vibelock.workers.dev/openapi.json
- MCP: `POST https://aziel-runtime.vibelock.workers.dev/mcp`
- Live skill (this markdown): `GET https://vibelock-download-tracker.vibelock.workers.dev/v1/skill`

Ops (do **not** increment downloads or views):

- `GET /v1/health` — liveness
- `GET /v1/skill` — this file
- Product POSTs listed in OpenAPI

Grok: import OpenAPI as a custom tool. ChatGPT: GPT Actions. Venice: HTTP tools.

## Example

```bash
curl -s -A 'Mozilla/5.0' https://vibelock-download-tracker.vibelock.workers.dev/v1/health
curl -s -A 'Mozilla/5.0' https://vibelock-download-tracker.vibelock.workers.dev/v1/skill
```

## Local (after one-click install)

```bash
curl -fsSL https://vibelock-download-tracker.vibelock.workers.dev/install.sh | bash
vibelock ui
vibelock doctor
```

Then open http://127.0.0.1:8760 (loopback only).

Counted download (gzip HTTP 200, no 302): https://vibelock-download-tracker.vibelock.workers.dev/download?asset=vibelock-0.2.0.tar.gz
GitHub: https://github.com/AzielEliab/vibelock

Paper: DOI https://doi.org/10.5281/zenodo.21431610 · https://zenodo.org/records/21431610 · Apache-2.0. Forks welcome.

## Catalog + local UI

Author: **Aziel Eliab**. Honest scope: Physical-consistency evaluation of speech audio. Risk assessment, not a liveness proof.

- Catalog product: https://aziel-runtime.vibelock.workers.dev/p/vibelock/
- Catalog OpenAPI: https://aziel-runtime.vibelock.workers.dev/openapi.json
- Catalog MCP: `POST https://aziel-runtime.vibelock.workers.dev/mcp`
- This Worker skill: `GET https://vibelock-download-tracker.vibelock.workers.dev/v1/skill`
- This Worker OpenAPI: https://vibelock-download-tracker.vibelock.workers.dev/openapi.json
- Sample payload: `GET https://vibelock-download-tracker.vibelock.workers.dev/v1/example`

Local UI: **Import JSON file** (`type=file`) and **Export JSON**. Then `vibelock doctor`.

Grok: import catalog or Worker OpenAPI as a custom tool. ChatGPT: GPT Actions. Venice: HTTP tools.
