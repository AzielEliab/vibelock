/**
 * VibeLock download tracker (Cloudflare Worker).
 *
 * Counts GitHub-release downloads across the canonical repo, its
 * branches, and forks. Forks are identified by GitHub owner/repo.
 *
 * Routes
 *   GET  /                         small index (links to GitHub Releases)
 *   GET  /stats                    JSON counts
 *   POST /event                    forks (or any replica) report a download
 *   GET  /download/:owner/:repo/:tag/:asset
 *                                  increment + 302 to GitHub release asset
 *   GET  /go?owner=&repo=&tag=&asset=&branch=&fork=
 *                                  same, query-string form
 *
 * KV binding: DOWNLOADS (see wrangler.toml). No secrets live in this tree.
 */

const STATS_KEY = "stats:v1";

const DEFAULTS = {
  project: "vibelock",
  owner: "AzielEliab",
  repo: "vibelock",
  branch: "main",
};

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

function json(body, status = 200) {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...corsHeaders() },
  });
}

function emptyStats() {
  return { total: 0, by_repo: {}, updated_at: null };
}

function repoKey(owner, repo) {
  return `${owner}/${repo}`;
}

function isFork(owner, repo, env) {
  const canonOwner = env.CANONICAL_OWNER || DEFAULTS.owner;
  const canonRepo = env.CANONICAL_REPO || DEFAULTS.repo;
  return !(
    String(owner).toLowerCase() === String(canonOwner).toLowerCase() &&
    String(repo).toLowerCase() === String(canonRepo).toLowerCase()
  );
}

async function readStats(env) {
  const raw = await env.DOWNLOADS.get(STATS_KEY);
  if (!raw) return emptyStats();
  try {
    const parsed = JSON.parse(raw);
    if (typeof parsed.total !== "number") return emptyStats();
    if (!parsed.by_repo || typeof parsed.by_repo !== "object") parsed.by_repo = {};
    return parsed;
  } catch {
    return emptyStats();
  }
}

async function writeStats(env, stats) {
  stats.updated_at = new Date().toISOString();
  await env.DOWNLOADS.put(STATS_KEY, JSON.stringify(stats));
}

function bump(stats, event) {
  const project = event.project || DEFAULTS.project;
  const owner = event.owner || DEFAULTS.owner;
  const repo = event.repo || DEFAULTS.repo;
  const branch = event.branch || DEFAULTS.branch;
  const tag = event.tag || null;
  const asset = event.asset || null;
  const fork = Boolean(event.fork);
  const key = repoKey(owner, repo);

  stats.total = (stats.total || 0) + 1;
  if (!stats.by_repo[key]) {
    stats.by_repo[key] = {
      project,
      owner,
      repo,
      fork,
      total: 0,
      branches: {},
      tags: {},
      assets: {},
    };
  }
  const row = stats.by_repo[key];
  row.project = project;
  row.owner = owner;
  row.repo = repo;
  row.fork = fork;
  row.total = (row.total || 0) + 1;
  row.branches[branch] = (row.branches[branch] || 0) + 1;
  if (tag) row.tags[tag] = (row.tags[tag] || 0) + 1;
  if (asset) row.assets[asset] = (row.assets[asset] || 0) + 1;
  return stats;
}

function githubAssetUrl(owner, repo, tag, asset) {
  const t = tag === "latest" ? "latest" : `download/${encodeURIComponent(tag)}`;
  if (tag === "latest") {
    // /latest/download/<asset> is the stable GitHub layout for the newest release.
    return `https://github.com/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/releases/latest/download/${encodeURIComponent(asset)}`;
  }
  return `https://github.com/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/releases/${t}/${encodeURIComponent(asset)}`;
}

function parseDownloadPath(pathname) {
  // /download/:owner/:repo/:tag/:asset   (asset may contain extra slashes → last join)
  const parts = pathname.split("/").filter(Boolean);
  if (parts[0] !== "download" || parts.length < 5) return null;
  const owner = parts[1];
  const repo = parts[2];
  const tag = parts[3];
  const asset = parts.slice(4).join("/");
  return { owner, repo, tag, asset };
}

async function recordAndRedirect(env, dims) {
  const owner = dims.owner || DEFAULTS.owner;
  const repo = dims.repo || DEFAULTS.repo;
  const fork = dims.fork != null ? Boolean(dims.fork) : isFork(owner, repo, env);
  const stats = await readStats(env);
  bump(stats, {
    project: dims.project || env.PROJECT || DEFAULTS.project,
    owner,
    repo,
    branch: dims.branch || DEFAULTS.branch,
    tag: dims.tag,
    asset: dims.asset,
    fork,
  });
  await writeStats(env, stats);
  const dest = githubAssetUrl(owner, repo, dims.tag || "latest", dims.asset);
  return Response.redirect(dest, 302);
}

function indexHtml(env) {
  const releases = env.GITHUB_RELEASES || "https://github.com/AzielEliab/vibelock/releases";
  return `<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>VibeLock downloads</title>
<body>
  <h1>VibeLock downloads</h1>
  <p>Sound can be forged. Physics is harder to fake.</p>
  <p><strong>Download releases:</strong> <a href="${releases}">${releases}</a></p>
  <p>Counts (canonical repo, branches, and forks): <a href="/stats">/stats</a></p>
  <p>Forks are welcome and always allowed. Report a download with POST /event.</p>
</body>
</html>`;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    if (url.pathname === "/" && request.method === "GET") {
      return new Response(indexHtml(env), {
        headers: { "Content-Type": "text/html; charset=utf-8", ...corsHeaders() },
      });
    }

    if (url.pathname === "/stats" && request.method === "GET") {
      const stats = await readStats(env);
      return json({
        project: env.PROJECT || DEFAULTS.project,
        dimensions: ["project", "owner", "repo", "branch", "fork"],
        note: "Forks are identified by GitHub owner/repo. Canonical tree is AzielEliab/vibelock.",
        ...stats,
      });
    }

    if (url.pathname === "/event" && request.method === "POST") {
      let body;
      try {
        body = await request.json();
      } catch {
        return json({ error: "JSON body required" }, 400);
      }
      const owner = body.owner || DEFAULTS.owner;
      const repo = body.repo || DEFAULTS.repo;
      if (typeof owner !== "string" || typeof repo !== "string") {
        return json({ error: "owner and repo must be strings" }, 400);
      }
      const fork = body.fork != null ? Boolean(body.fork) : isFork(owner, repo, env);
      const stats = await readStats(env);
      bump(stats, {
        project: body.project || env.PROJECT || DEFAULTS.project,
        owner,
        repo,
        branch: body.branch || DEFAULTS.branch,
        tag: body.tag || null,
        asset: body.asset || null,
        fork,
      });
      await writeStats(env, stats);
      return json({ ok: true, total: stats.total, repo: repoKey(owner, repo), fork });
    }

    if (request.method === "GET" && url.pathname.startsWith("/download/")) {
      const parsed = parseDownloadPath(url.pathname);
      if (!parsed) {
        return json({ error: "usage: /download/:owner/:repo/:tag/:asset" }, 400);
      }
      return recordAndRedirect(env, {
        ...parsed,
        project: url.searchParams.get("project"),
        branch: url.searchParams.get("branch"),
        fork: url.searchParams.has("fork")
          ? url.searchParams.get("fork") === "true"
          : undefined,
      });
    }

    if (request.method === "GET" && url.pathname === "/go") {
      const asset = url.searchParams.get("asset");
      if (!asset) return json({ error: "asset query param required" }, 400);
      return recordAndRedirect(env, {
        owner: url.searchParams.get("owner"),
        repo: url.searchParams.get("repo"),
        tag: url.searchParams.get("tag") || "latest",
        asset,
        branch: url.searchParams.get("branch"),
        project: url.searchParams.get("project"),
        fork: url.searchParams.has("fork")
          ? url.searchParams.get("fork") === "true"
          : undefined,
      });
    }

    return json({ error: "not found" }, 404);
  },
};
