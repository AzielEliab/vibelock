# VibeLock download tracker (Cloudflare Worker)

Counts downloads of GitHub release assets for VibeLock **across the
canonical repository, other branches, and forks**. Forks are identified
by GitHub `owner/repo`.

No secrets belong in this directory. KV namespace IDs in
`wrangler.toml` are placeholders until you create a namespace.

## Bindings

| Binding     | Type | Purpose                                      |
|-------------|------|----------------------------------------------|
| `DOWNLOADS` | KV   | JSON blob of counts keyed `stats:v1`         |

Vars (not secrets): `PROJECT`, `CANONICAL_OWNER`, `CANONICAL_REPO`,
`GITHUB_RELEASES`.

## Deploy

```bash
cd workers/download-tracker

# 1. Log in once (opens a browser; token stays in wrangler, not in git)
npx wrangler login

# 2. Create the KV namespace. Paste the id into wrangler.toml
#    as kv_namespaces.id (binding name MUST stay DOWNLOADS).
npx wrangler kv namespace create DOWNLOADS
npx wrangler kv namespace create DOWNLOADS --preview

# 3. Deploy
npx wrangler deploy
```

Point `downloads.vibelock.dev` at the worker when DNS is ready. Until
then, the `workers.dev` subdomain wrangler prints is enough.

## Routes

| Method | Path | Behavior |
|--------|------|----------|
| GET | `/` | Index page with the GitHub Releases link |
| GET | `/stats` | JSON counts, dimensions `project, owner, repo, branch, fork` |
| POST | `/event` | A fork (or any replica) reports a download |
| GET | `/download/:owner/:repo/:tag/:asset` | Increment, 302 to GitHub |
| GET | `/go?owner=&repo=&tag=&asset=&branch=` | Same, query-string form |

Tracked download (canonical):

```
https://downloads.vibelock.dev/download/AzielEliab/vibelock/latest/vibelock-0.1.0.tar.gz
```

A fork reports its own asset:

```bash
curl -X POST https://downloads.vibelock.dev/event \
  -H "content-type: application/json" \
  -d '{
    "project": "vibelock",
    "owner": "YourFork",
    "repo": "vibelock",
    "branch": "main",
    "fork": true,
    "tag": "v0.1.0",
    "asset": "vibelock-0.1.0.tar.gz"
  }'
```

`fork` is inferred from `owner/repo` versus `AzielEliab/vibelock` when
omitted.

## Dimensions

Every increment stores:

- `project` (default `vibelock`)
- `owner`, `repo` — GitHub identity of the tree that was downloaded
- `branch` (default `main`; pass `?branch=` on `/download/...`)
- `fork` — `true` when `owner/repo` is not the canonical tree
- optional `tag` and `asset`

The worker redirects. It does not proxy bytes, so GitHub remains the
file host.
