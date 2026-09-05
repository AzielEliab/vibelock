# VibeLock Worker (Cloudflare)

The Worker homepage is a **full product UI** for Aziel Eliab — in-browser
risk analysis plus counted download and one-click install. It is not a
thin downloads landing page.

Live: https://vibelock-download-tracker.vibelock.workers.dev/

Title: **VibeLock — Aziel Eliab**. Black/gold styling, everblooming
sigil, SEO (description, canonical, Open Graph, JSON-LD
`SoftwareApplication`, robots-friendly meta), cite block, `cite.json`,
`llms.txt`. Identity is **Aziel Eliab only**. Apache-2.0. Forks welcome.

The Analyze workspace posts to `/v1/analyze` (same keys as the package
UI / `vibelock/ui.py`). Paste notes, fill feature fields, or upload a
WAV/still. Results show score, verdict, reason codes, and per-check
metrics — software output, not a raw JSON dump. Physics + A/V deepfake
detection is a **risk assessment**, not a lie detector and not courtroom
proof. Hosted is not a live mic. `/v1` does not increment downloads.

**This worker must be deployed** before `https://downloads.vibelock.dev`
resolves. Until then, send people to the `workers.dev` URL above or
[GitHub Releases](https://github.com/AzielEliab/vibelock/releases).

No secrets belong in this directory. The KV namespace id in
`wrangler.toml` is live (`21a88662123a4be2ad544a9e401de38e`).

## Bindings

| Binding     | Type | Purpose |
|-------------|------|---------|
| `DOWNLOADS` | KV   | Counters keyed `project|owner|repo|branch|fork` plus `__views__` / `__uses__` |
| `ASSETS`    | dir  | Counted tarball + `sigil.png` |

## Deploy

```bash
cd workers/download-tracker

# 1. Log in once (opens a browser; token stays in wrangler, not in git)
npx wrangler login

# 2. KV namespace already exists (binding DOWNLOADS). Only create if you
#    are standing up a new account — then paste the id into wrangler.toml.
# npx wrangler kv namespace create DOWNLOADS

# 3. Deploy
npx wrangler deploy
```

Point `downloads.vibelock.dev` at the worker when DNS is ready. Until
then, the `workers.dev` subdomain wrangler prints is enough.

If `wrangler whoami` says you are not authenticated, run `npx wrangler
login` on a machine with a browser, then `npx wrangler deploy` from
`workers/download-tracker`.

## Routes

| Method | Path | Behavior |
|--------|------|----------|
| GET | `/` | Product UI: analyze workspace + views/downloads + Download + one-click install |
| GET | `/download?repo=&tag=&asset=` | Increment KV, **200 gzip** from Worker ASSETS (`vibelock-0.3.0.tar.gz`). Not a 302 to GitHub. |
| GET | `/stats` | JSON totals plus per-repo and per-branch breakdown |
| POST | `/event` | A fork reports a download |
| GET | `/cite.json` | Citation (author Aziel Eliab; no invented DOI) |
| GET | `/llms.txt` | Robots-friendly product brief |
| GET | `/robots.txt` | Allow `/` |

Query params on `/download`: `owner`, `repo` (`AzielEliab/vibelock` is
accepted), `branch`, `fork` (`1` or `owner/repo`), `tag`, `asset`.

Default redirect with no asset:

```
https://github.com/AzielEliab/vibelock/releases/latest
```

Tracked asset URL (after deploy):

```
https://downloads.vibelock.dev/download?repo=AzielEliab/vibelock&tag=latest&asset=vibelock-0.3.0.tar.gz
```

A fork reports its own download:

```bash
curl -X POST https://downloads.vibelock.dev/event   -H "content-type: application/json"   -d '{
    "owner": "YourFork",
    "repo": "vibelock",
    "branch": "main",
    "fork": "1",
    "asset": "vibelock-0.3.0.tar.gz"
  }'
```

`fork=1` or `fork=YourFork/vibelock`. If `owner/repo` is not
`AzielEliab/vibelock`, the worker records `fork=1` automatically.

## Stats

`GET /stats` returns `total`, `views`, `uses`, `by_repo`, `by_branch`,
`by_fork`, and a `breakdown` array so forks can read aggregates.

## CORS

All responses include `Access-Control-Allow-Origin: *`.

## Use with Grok, ChatGPT, Venice

This Worker also hosts the product runtime API (CORS `*`). `/v1` routes do **not** increment `DOWNLOADS`.

| Method | Path | Notes |
|--------|------|-------|
| GET | `/v1/health` | Liveness |
| GET | `/v1/skill` | Live SKILL.md |
| POST | `/v1/analyze` | Advisory multi-signal score (features / limited PCM / visual / pitch / A/V) |
| POST | `/v1/detect` | Same engine; deepfake-oriented body |
| GET | `/openapi.json` | OpenAPI 3.1 |
| GET | `/ai` | ChatGPT Actions, Grok/xAI tools, Venice HTTP tools; MCP catalog |

See the product README section **Use with Grok, ChatGPT, Venice**.
OpenAPI: https://vibelock-download-tracker.vibelock.workers.dev/openapi.json
