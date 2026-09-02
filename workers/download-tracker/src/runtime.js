/**
 * VibeLock hosted runtime (Cloudflare Worker).
 * Ports scoring heuristics as far as JS allows.
 * Risk assessment, not a liveness proof. Hosted is not a live mic.
 */
function runtimeCors() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

function runtimeJson(body, status = 200) {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...runtimeCors() },
  });
}

async function sha256Hex(bytes) {
  const data = bytes instanceof Uint8Array ? bytes : new TextEncoder().encode(String(bytes));
  const dig = await crypto.subtle.digest("SHA-256", data);
  const arr = new Uint8Array(dig);
  let out = "";
  for (let i = 0; i < arr.length; i++) out += arr[i].toString(16).padStart(2, "0");
  return out;
}

async function readJsonBody(request) {
  const ct = (request.headers.get("content-type") || "").toLowerCase();
  if (request.method === "GET" || request.method === "HEAD") return {};
  const text = await request.text();
  if (!text || !text.trim()) return {};
  try {
    return JSON.parse(text);
  } catch {
    const err = new Error("JSON body required");
    err.status = 400;
    throw err;
  }
}

function utcNow() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

function aiHowTo(base) {
  const openapi = base + "/openapi.json";
  const health = base + "/v1/health";
  return {
    chatgpt_actions: [
      "Open GPT Editor → Actions → Import from URL",
      "Paste " + openapi,
      "Authentication: None",
      "Allow GET /v1/health and the listed POST /v1 routes",
      "Test GET /v1/health, then a sample POST from the spec",
    ],
    grok_xai_tools: [
      "Add an HTTP / OpenAPI tool pointing at " + openapi,
      "Or register GET /v1/health, GET /openapi.json, and the product POSTs",
      "No API key. CORS is *",
    ],
    venice_http_tools: [
      "Add an HTTP tool with method, URL, and JSON body from " + openapi,
      "Start with GET " + health,
      "Then call the product POST listed in the spec",
    ],
    mcp_catalog: "https://aziel-runtime.vibelock.workers.dev/mcp",
    notes: [
      "GET /download still serves the gzip tarball and increments the counter.",
      "/v1, /openapi.json, and /ai do not increment DOWNLOADS.",
    ],
  };
}

const PRODUCT = "vibelock";
const VERSION = "0.2.0";
const BASE = "https://vibelock-download-tracker.vibelock.workers.dev";
const MOTTO = "Sound can be forged. Physics is harder to fake.";
const LABEL = "Audio authenticity advisory, not courtroom proof.";
const HOSTED_NOTE = "Hosted endpoint is not a live microphone. Desktop `listen` stays local.";
const MAX_PCM_BYTES = 65536;
const MAX_SAMPLES = 32000;
const AUDIO_WEIGHTS = {
  spectral: 0.18,
  phase_continuity: 0.22,
  formant: 0.22,
  decay: 0.16,
  temporal: 0.14,
  buzz: 0.08,
};

function clip01(x) { return Math.min(1, Math.max(0, Number(x) || 0)); }
function logisticScore(value, good, bad) {
  if (good === bad) return 0.5;
  let t = (value - bad) / (good - bad);
  t = clip01(t);
  return t * t * (3.0 - 2.0 * t);
}
function num(v, d) {
  const n = Number(v);
  return Number.isFinite(n) ? n : d;
}

function b64ToBytes(b64) {
  const s = String(b64).replace(/\s+/g, "");
  const bin = atob(s);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function pcmToFloat(bytes, dtype) {
  if (dtype === "f32") {
    if (bytes.byteLength % 4 !== 0) throw new Error("pcm_b64 f32 length invalid");
    const aligned = bytes.byteOffset % 4 === 0 ? bytes : bytes.slice();
    return new Float32Array(aligned.buffer, aligned.byteOffset, aligned.byteLength / 4);
  }
  if (bytes.byteLength % 2 !== 0) throw new Error("pcm_b64 int16 length invalid");
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const n = bytes.byteLength / 2;
  const x = new Float64Array(n);
  for (let i = 0; i < n; i++) x[i] = view.getInt16(i * 2, true) / 32768;
  return x;
}

function rmsOf(x) {
  if (!x.length) return 0;
  let s = 0;
  for (let i = 0; i < x.length; i++) s += x[i] * x[i];
  return Math.sqrt(s / x.length);
}

function zcrOf(x) {
  if (x.length < 2) return 0;
  let c = 0;
  for (let i = 1; i < x.length; i++) {
    if ((x[i] >= 0 && x[i - 1] < 0) || (x[i] < 0 && x[i - 1] >= 0)) c++;
  }
  return c / (x.length - 1);
}

function peakOf(x) {
  let p = 0;
  for (let i = 0; i < x.length; i++) {
    const a = Math.abs(x[i]);
    if (a > p) p = a;
  }
  return p;
}

function envelopeStats(x, hop) {
  const hopN = Math.max(1, hop | 0);
  const nWin = Math.max(8, hopN * 2);
  const env = [];
  for (let i = 0; i + nWin <= x.length; i += hopN) {
    let s = 0;
    for (let j = 0; j < nWin; j++) s += x[i + j] * x[i + j];
    env.push(Math.sqrt(s / nWin));
  }
  if (env.length < 2) return { var: 0, maxJump: 0, n: env.length };
  const mean = env.reduce((a, b) => a + b, 0) / env.length;
  let v = 0;
  let maxJump = 0;
  for (let i = 0; i < env.length; i++) v += (env[i] - mean) * (env[i] - mean);
  for (let i = 1; i < env.length; i++) {
    const j = Math.abs(Math.log((env[i] + 1e-8) / (env[i - 1] + 1e-8)));
    if (j > maxJump) maxJump = j;
  }
  return { var: v / env.length, maxJump, n: env.length };
}

function coarseCentroid(x, sr) {
  // 8-band energy via simple downsample folding (not an FFT).
  const bands = new Float64Array(8);
  const step = Math.max(1, Math.floor(x.length / 2048));
  for (let i = 0; i < x.length; i += step) {
    const s = Math.abs(x[i]);
    const t = i / sr;
    const k = Math.min(7, Math.floor((i / x.length) * 8));
    bands[k] += s;
  }
  let tot = 0, wsum = 0;
  for (let k = 0; k < 8; k++) { tot += bands[k]; wsum += bands[k] * (k + 0.5); }
  if (tot <= 0) return 0;
  return (wsum / tot) / 8;
}

function featuresFromPcm(x, sr) {
  const rms = rmsOf(x);
  const zcr = zcrOf(x);
  const peak = peakOf(x);
  const crest = peak / (rms + 1e-12);
  const env = envelopeStats(x, Math.max(1, Math.round(0.01 * sr)));
  const centroid = coarseCentroid(x, sr);
  return { rms, zcr, peak, crest, rms_var: env.var, env_jump: env.maxJump, centroid, n_samples: x.length, sample_rate: sr };
}

function checksFromFeatures(f) {
  const notes = [LABEL, HOSTED_NOTE];
  const checks = [];
  const rms = num(f.rms, NaN);
  const zcr = num(f.zcr, NaN);
  const peak = num(f.peak, NaN);
  const crest = num(f.crest, peak / (rms + 1e-12));
  const rmsVar = num(f.rms_var, num(f.zcr_var, 0));
  const envJump = num(f.env_jump, num(f.flux, 0));
  const centroid = num(f.centroid, num(f.spectral_centroid, 0.4));
  const fine = num(f.fine_var, num(f.spectral_flatness, 0.15));
  const formantJump = num(f.formant_jump_hz, num(f.median_jump_hz, 40));
  const decayTau = num(f.decay_tau_s, 0.02);
  const buzzRatio = num(f.buzz_ratio, num(f.peak_to_med, 4));

  let specScore = logisticScore(fine, 0.08, 0.005);
  const specHigh = logisticScore(fine, 0.25, 1.60);
  specScore = clip01(Math.min(specScore, specHigh));
  let specCode = null;
  if (fine < 0.012 || fine > 1.20) { specCode = "SPECTRAL_UNNATURAL"; specScore = Math.min(specScore, 0.40); }
  if (centroid > 0 && (centroid < 0.08 || centroid > 0.92)) {
    specCode = specCode || "SPECTRAL_UNNATURAL";
    specScore = Math.min(specScore, 0.45);
  }
  checks.push({ name: "spectral", score: specScore, reason_code: specCode, metrics: { fine_var: fine, centroid }, note: "Log-spectral stand-in from provided features or coarse centroid." });

  const zcrScore = Number.isFinite(zcr) ? clip01(Math.min(logisticScore(zcr, 0.08, 0.002), logisticScore(zcr, 0.12, 0.45))) : 0.5;
  let phaseCode = null;
  let phaseScore = zcrScore;
  if (Number.isFinite(zcr) && zcr > 0.35) { phaseCode = "PHASE_DISCONTINUITY"; phaseScore = Math.min(phaseScore, 0.35); }
  else if (Number.isFinite(zcr) && zcr < 0.004 && Number.isFinite(rms) && rms > 0.02) { phaseCode = "PHASE_OVERFLAT"; phaseScore = Math.min(phaseScore, 0.40); }
  checks.push({ name: "phase_continuity", score: phaseScore, reason_code: phaseCode, metrics: { zcr }, note: "ZCR stand-in for Hilbert phase (JS has no Hilbert)." });

  let formScore = logisticScore(formantJump, 50.0, 150.0);
  let formCode = null;
  if (formantJump > 110) { formCode = "FORMANT_UNSTABLE"; formScore = Math.min(formScore, 0.35); }
  checks.push({ name: "formant", score: clip01(formScore), reason_code: formCode, metrics: { median_jump_hz: formantJump }, note: "Formant jump if provided; otherwise a mid default (not LPC)." });

  let decayScore = logisticScore(decayTau, 0.02, 0.20);
  let decayCode = null;
  if (decayTau > 0.08 || decayTau < 0.001) { decayCode = "DECAY_IMPLAUSIBLE"; decayScore = Math.min(decayScore, 0.4); }
  checks.push({ name: "decay", score: clip01(decayScore), reason_code: decayCode, metrics: { decay_tau_s: decayTau }, note: "Anatomical decay window 1–80 ms when tau is provided." });

  let tempScore = logisticScore(envJump, 0.4, 2.5);
  let tempCode = null;
  if (envJump > 1.8) { tempCode = "TEMPORAL_SPLICE"; tempScore = Math.min(tempScore, 0.35); }
  checks.push({ name: "temporal", score: clip01(tempScore), reason_code: tempCode, metrics: { env_jump: envJump, rms_var: rmsVar }, note: "Envelope jump stand-in for coincident RMS/flux splices." });

  let buzzScore = logisticScore(buzzRatio, 6.0, 20.0);
  let buzzCode = null;
  if (buzzRatio > 12) { buzzCode = "VOCODER_BUZZ"; buzzScore = Math.min(buzzScore, 0.40); }
  checks.push({ name: "buzz", score: clip01(buzzScore), reason_code: buzzCode, metrics: { peak_to_med: buzzRatio }, note: "Modulation-spectrum peak ratio if provided." });

  if (Number.isFinite(rms) && rms < 1e-6) {
    notes.push("Near-silent RMS; score is a risk assessment on a weak signal.");
  }
  return { checks, notes };
}

function combine(checks) {
  let nume = 0, den = 0;
  for (const [name, w] of Object.entries(AUDIO_WEIGHTS)) {
    const vals = checks.filter((c) => c.name === name).map((c) => c.score);
    if (!vals.length) continue;
    const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
    nume += w * mean;
    den += w;
  }
  const score = clip01(den > 0 ? nume / den : 0);
  const codes = [];
  for (const c of checks) {
    if (c.reason_code && !codes.includes(c.reason_code)) codes.push(c.reason_code);
  }
  return { score, reason_codes: codes };
}

function openapiDoc() {
  return {
    openapi: "3.1.0",
    info: {
      title: "VibeLock Runtime API",
      version: VERSION,
      summary: MOTTO,
      description: LABEL + " " + HOSTED_NOTE,
    },
    servers: [{ url: BASE }],
    paths: {
      "/v1/health": { get: { operationId: "vibelockHealth", summary: "Liveness", responses: { "200": { description: "OK" } } } },
      "/v1/analyze": {
        post: {
          operationId: "vibelockAnalyze",
          summary: "Audio-only risk assessment from features or limited PCM",
          requestBody: {
            required: true,
            content: {
              "application/json": {
                schema: {
                  type: "object",
                  properties: {
                    features: { type: "object", properties: { rms: { type: "number" }, zcr: { type: "number" } }, additionalProperties: true },
                    pcm_b64: { type: "string", description: "Limited int16 LE (default) or f32 PCM, not a live mic" },
                    rate: { type: "integer" },
                    sample_rate: { type: "integer" },
                    pcm_dtype: { type: "string", enum: ["int16", "f32"] },
                  },
                },
              },
            },
          },
          responses: { "200": { description: "Risk assessment (not a liveness proof)" } },
        },
      },
    },
  };
}

async function handleAnalyze(body) {
  body = body || {};
  let features = body.features && typeof body.features === "object" ? { ...body.features } : null;
  let n_samples = num(features && features.n_samples, 0);
  let sr = num(body.rate, num(body.sample_rate, num(features && features.sample_rate, 16000))) | 0;
  if (sr < 8000 || sr > 48000) sr = 16000;
  let mode = "features";
  if (!features && body.pcm_b64) {
    let bytes;
    try { bytes = b64ToBytes(body.pcm_b64); }
    catch { return runtimeJson({ ok: false, error: "pcm_b64 is not valid base64", label: LABEL, hosted_mic: false }, 400); }
    if (bytes.byteLength > MAX_PCM_BYTES) {
      return runtimeJson({ ok: false, error: "pcm too large", max_bytes: MAX_PCM_BYTES, label: LABEL, hosted_mic: false }, 413);
    }
    let x;
    try { x = pcmToFloat(bytes, body.pcm_dtype === "f32" ? "f32" : "int16"); }
    catch (e) { return runtimeJson({ ok: false, error: e.message, label: LABEL, hosted_mic: false }, 400); }
    if (x.length > MAX_SAMPLES) x = x.subarray(0, MAX_SAMPLES);
    features = featuresFromPcm(x, sr);
    n_samples = x.length;
    mode = "pcm_limited";
  }
  if (!features) {
    return runtimeJson({ ok: false, error: "provide features:{rms,zcr,...} or pcm_b64+rate", label: LABEL, hosted_mic: false, listen: "local" }, 400);
  }
  const { checks, notes } = checksFromFeatures(features);
  const comb = combine(checks);
  return runtimeJson({
    ok: true,
    product: PRODUCT,
    label: LABEL,
    liveness_proof: false,
    hosted_mic: false,
    listen: "local",
    mode,
    score: comb.score,
    reason_codes: comb.reason_codes,
    checks,
    features,
    sample_rate: sr,
    n_samples,
    notes,
    motto: MOTTO,
    limitation: LABEL,
    courtroom_proof: false,
    advisory: true,
  });
}

export async function handleRuntime(request, url, env) {
  const path = url.pathname;
  if (path === "/v1/health" && request.method === "GET") {
    return runtimeJson({ ok: true, product: PRODUCT, version: VERSION, label: LABEL, hosted_mic: false, liveness_proof: false, courtroom_proof: false, advisory: true });
  }
  if (path === "/openapi.json" && request.method === "GET") return runtimeJson(openapiDoc());
  if (path === "/ai" && request.method === "GET") {
    return runtimeJson({
      product: PRODUCT,
      title: "Use with Grok, ChatGPT, Venice",
      motto: MOTTO,
      label: LABEL,
      openapi: BASE + "/openapi.json",
      health: BASE + "/v1/health",
      ...aiHowTo(BASE),
    });
  }
  if (path === "/v1" && request.method === "GET") {
    return runtimeJson({ product: PRODUCT, label: LABEL, endpoints: ["GET /v1/health", "POST /v1/analyze", "GET /openapi.json", "GET /ai"] });
  }
  if (path === "/v1/analyze" && request.method === "POST") {
    let body = {};
    try { body = await readJsonBody(request); } catch (e) { return runtimeJson({ ok: false, error: e.message, label: LABEL }, e.status || 400); }
    return handleAnalyze(body);
  }
  if (path === "/v1/analyze") return runtimeJson({ error: "method not allowed" }, 405);
  if (path.startsWith("/v1/")) return runtimeJson({ error: "not found", product: PRODUCT }, 404);
  return null;
}
