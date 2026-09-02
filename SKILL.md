---
name: VibeLock
description: Use when calling VibeLock hosted /v1 or installing the local package. Author Aziel Eliab.
---

# VibeLock

Physical-consistency evaluation of speech audio. Risk assessment, not a liveness proof. Hosted is not a live mic. Not courtroom audio proof. Author: Aziel Eliab.

**THIS IS:** physical-consistency evaluation of speech audio (local CLI + hosted advisory /v1/analyze).

**THIS IS NOT:** courtroom audio proof, a liveness detector, a live microphone, or a claim that physics cannot be forged.

Author: **Aziel Eliab**. Forks are welcome and always allowed. Apache-2.0.

Always send `User-Agent: Mozilla/5.0`. Cloudflare Workers may 403 an empty agent.

## Call these URLs

- Worker OpenAPI: https://vibelock-download-tracker.vibelock.workers.dev/openapi.json
- Catalog OpenAPI: https://aziel-runtime.vibelock.workers.dev/openapi.json
- MCP: `POST https://aziel-runtime.vibelock.workers.dev/mcp`
- Live skill (this markdown): `GET https://vibelock-download-tracker.vibelock.workers.dev/v1/skill`

Ops (do **not** increment downloads or views):

| Method | Path | What |
|--------|------|------|
| GET | `/v1/health` | Liveness. Does not increment downloads. |
| GET | `/v1/skill` | This markdown. Does not increment downloads. |
| POST | `/v1/analyze` | Advisory physical-consistency score of posted audio metadata/features. Not a live mic. |

Grok: import OpenAPI as a custom tool. ChatGPT: GPT Actions. Venice: HTTP tools.

## Example

```bash
curl -s -A 'Mozilla/5.0' https://vibelock-download-tracker.vibelock.workers.dev/v1/health
curl -s -A 'Mozilla/5.0' https://vibelock-download-tracker.vibelock.workers.dev/v1/skill
curl -s -A 'Mozilla/5.0' -X POST https://vibelock-download-tracker.vibelock.workers.dev/v1/analyze \
  -H 'content-type: application/json' \
  -d '{"note":"advisory features only; not a live mic"}'
```

## Local (after one-click install)

```bash
curl -fsSL https://vibelock-download-tracker.vibelock.workers.dev/install.sh | bash
vibelock ui
```

Then open http://127.0.0.1:8760 (loopback only).

DOI: https://doi.org/10.5281/zenodo.21431610  
Record: https://zenodo.org/records/21431610  

Counted download (gzip HTTP 200, no 302): https://vibelock-download-tracker.vibelock.workers.dev/download?asset=vibelock-0.2.0.tar.gz
GitHub: https://github.com/AzielEliab/vibelock
