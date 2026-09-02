# VibeLock download tracker (Cloudflare Worker)

Counts GitHub-release downloads for VibeLock across the canonical
repository, other branches, and forks. Forks are identified by GitHub
`owner/repo`.

**This worker must be deployed** before `https://downloads.vibelock.dev`
resolves. Until then, send people to
[GitHub Releases](https://github.com/AzielEliab/vibelock/releases).

No secrets belong in this directory. The KV namespace id in
`wrangler.toml` is the placeholder `REPLACE_ME` until you create a
namespace.

## Bindings

| Binding     | Type | Purpose |
|-------------|------|---------|
| `DOWNLOADS` | KV   | Counters keyed `project|owner|repo|branch|fork` |

## Deploy

```bash
cd workers/download-tracker

# 1. Log in once (opens a browser; token stays in wrangler, not in git)
npx wrangler login

# 2. Create the KV namespace. Paste the id into wrangler.toml
#    replacing REPLACE_ME. Binding name MUST stay DOWNLOADS.
npx wrangler kv namespace create DOWNLOADS

# 3. Deploy
npx wrangler deploy
```

Point `downloads.vibelock.dev` at the worker when DNS is ready. Until
then, the `workers.dev` subdomain wrangler prints is enough.

## Routes

| Method | Path | Behavior |
|--------|------|----------|
| GET | `/` | Index page with the GitHub Releases link |
| GET | `/download?repo=&tag=&asset=` | Increment KV, **200 gzip** from Worker ASSETS (`vibelock-0.2.0.tar.gz`). Not a 302 to GitHub. |
| GET | `/stats` | JSON totals plus per-repo and per-branch breakdown |
| POST | `/event` | A fork reports a download |

Query params on `/download`: `owner`, `repo` (`AzielEliab/vibelock` is
accepted), `branch`, `fork` (`1` or `owner/repo`), `tag`, `asset`.

Default redirect with no asset:

```
https://github.com/AzielEliab/vibelock/releases/latest
```

Tracked asset URL (after deploy):

```
https://downloads.vibelock.dev/download?repo=AzielEliab/vibelock&tag=latest&asset=vibelock-0.2.0.tar.gz
```

A fork reports its own download:

```bash
curl -X POST https://downloads.vibelock.dev/event   -H "content-type: application/json"   -d '{
    "owner": "YourFork",
    "repo": "vibelock",
    "branch": "main",
    "fork": "1",
    "asset": "vibelock-0.2.0.tar.gz"
  }'
```

`fork=1` or `fork=YourFork/vibelock`. If `owner/repo` is not
`AzielEliab/vibelock`, the worker records `fork=1` automatically.

## Stats

`GET /stats` returns `total`, `by_repo`, `by_branch`, `by_fork`, and a
`breakdown` array so forks can read aggregates.

## CORS

All responses include `Access-Control-Allow-Origin: *`.

## Use with Grok, ChatGPT, Venice

This Worker also hosts the product runtime API (CORS `*`). `/v1` routes do **not** increment `DOWNLOADS`.

| Method | Path | Notes |
|--------|------|-------|
| GET | `/v1/health` | Liveness |
| GET | `/openapi.json` | OpenAPI 3.1 |
| GET | `/ai` | ChatGPT Actions, Grok/xAI tools, Venice HTTP tools; MCP catalog |

See the product README section **Use with Grok, ChatGPT, Venice**.
OpenAPI: https://vibelock-download-tracker.vibelock.workers.dev/openapi.json
