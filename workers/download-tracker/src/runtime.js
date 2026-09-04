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
const SKILL_MARKDOWN = "---\nname: VibeLock\ndescription: Use when calling VibeLock hosted /v1 or installing the local package for physics + A/V deepfake detection. Author Aziel Eliab.\n---\n\n# VibeLock\n\nPhysics + A/V deepfake detection. Risk assessment, not courtroom proof. Author: **Aziel Eliab**.\n\n**THIS IS:** a multi-signal detector — vocal-tract / vibration physics, spatial image artifacts, temporal video flicker/flow, unnatural pitch/phase shifts, and talking-head A/V sync (local CLI + hosted advisory `/v1/analyze` and `/v1/detect`).\n\n**THIS IS NOT:** courtroom proof, a liveness detector, a live microphone, face recognition, or a claim that physics cannot be forged. Hosted `/v1` does not increment downloads or views.\n\nAlways send `User-Agent: Mozilla/5.0`. Cloudflare Workers may 403 an empty agent.\n\n## Call these URLs\n\n- Worker OpenAPI: https://vibelock-download-tracker.vibelock.workers.dev/openapi.json\n- Catalog OpenAPI: https://aziel-runtime.vibelock.workers.dev/openapi.json\n- MCP: `POST https://aziel-runtime.vibelock.workers.dev/mcp`\n- Live skill (this markdown): `GET https://vibelock-download-tracker.vibelock.workers.dev/v1/skill`\n\nOps (do **not** increment downloads or views):\n\n- `GET /v1/health` — liveness\n- `GET /v1/skill` — this file\n- `POST /v1/analyze` — advisory score from audio features/PCM and/or visual/pitch/A/V features\n- `POST /v1/detect` — same engine, deepfake-oriented request body\n\nGrok: import OpenAPI as a custom tool. ChatGPT: GPT Actions. Venice: HTTP tools.\n\n## Example\n\n```bash\ncurl -s -A 'Mozilla/5.0' https://vibelock-download-tracker.vibelock.workers.dev/v1/health\ncurl -s -A 'Mozilla/5.0' https://vibelock-download-tracker.vibelock.workers.dev/v1/skill\ncurl -s -A 'Mozilla/5.0' -X POST https://vibelock-download-tracker.vibelock.workers.dev/v1/detect \\\n  -H 'content-type: application/json' \\\n  -d '{\"features\":{\"rms\":0.08,\"zcr\":0.07},\"visual\":{\"blockiness\":1.8,\"noise_cv\":0.7},\"pitch\":{\"f0_jump\":8.5}}'\n```\n\n## Local (after one-click install)\n\n```bash\ncurl -fsSL https://vibelock-download-tracker.vibelock.workers.dev/install.sh | bash\nvibelock ui\nvibelock doctor\nvibelock detect path/to/media.png\n```\n\nThen open http://127.0.0.1:8760 (loopback only). WAV, PNG, PPM, `.vlvd` frame stacks.\n\nCounted download (gzip HTTP 200, no 302): https://vibelock-download-tracker.vibelock.workers.dev/download?asset=vibelock-0.3.0.tar.gz\nGitHub: https://github.com/AzielEliab/vibelock\n\nPaper: DOI https://doi.org/10.5281/zenodo.21431610 · https://zenodo.org/records/21431610 · Apache-2.0. Forks welcome.\n";
const VERSION = "0.3.0";
const BASE = "https://vibelock-download-tracker.vibelock.workers.dev";
const MOTTO = "Sound can be forged. Pixels can be forged. Physics is harder to fake.";
const LABEL = "Media authenticity advisory (audio, image, and video), not courtroom proof.";
const HOSTED_NOTE = "Hosted endpoint is not a live microphone. Desktop `listen` stays local. Hosted does not decode pixels; send visual/pitch/av features or limited PCM.";
const MAX_PCM_BYTES = 65536;
const MAX_SAMPLES = 32000;
const AUDIO_WEIGHTS = {
  spectral: 0.16,
  phase_continuity: 0.20,
  formant: 0.20,
  decay: 0.14,
  temporal: 0.12,
  buzz: 0.07,
  pitch: 0.11,
};
const VISUAL_WEIGHTS = {
  spatial_freq: 0.22,
  noise: 0.18,
  block: 0.12,
  chroma: 0.16,
  blend: 0.16,
  lighting: 0.16,
};
const TEMPORAL_WEIGHTS = {
  flicker: 0.28,
  motion: 0.26,
  identity: 0.24,
  interp: 0.22,
};
const AV_WEIGHT = 0.15;

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
  const pitch = pitchFromPcm(x, sr);
  return { rms, zcr, peak, crest, rms_var: env.var, env_jump: env.maxJump, centroid, n_samples: x.length, sample_rate: sr, ...pitch };
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

  const f0Jump = num(f.f0_jump, num(f.max_semitone_jump, 1.2));
  const f0Cv = num(f.f0_cv, 0.04);
  let pitchScore = clip01(Math.min(logisticScore(f0Jump, 1.8, 9.0), logisticScore(f0Cv, 0.035, 0.004)));
  let pitchCode = null;
  if (f0Jump > 7) { pitchCode = "PITCH_JUMP"; pitchScore = Math.min(pitchScore, 0.22); }
  else if (f0Cv < 0.008) { pitchCode = "PITCH_OVERFLAT"; pitchScore = Math.min(pitchScore, 0.28); }
  checks.push({ name: "pitch", score: pitchScore, reason_code: pitchCode, metrics: { f0_jump: f0Jump, f0_cv: f0Cv }, note: "F0 contour jump / flatness if provided or estimated from PCM." });

  if (Number.isFinite(rms) && rms < 1e-6) {
    notes.push("Near-silent RMS; score is a risk assessment on a weak signal.");
  }
  return { checks, notes };
}

function visualChecks(v) {
  v = v || {};
  const checks = [];
  const peak = num(v.spec_peak_ratio, num(v.freq_peak, 3.0));
  const lattice = num(v.lattice_ratio, 1.1);
  let freqScore = clip01(Math.min(logisticScore(peak, 3.2, 14.0), logisticScore(lattice, 1.15, 3.4)));
  let freqCode = null;
  if (peak > 8.5 || lattice > 2.2) { freqCode = "FREQ_FINGERPRINT"; freqScore = Math.min(freqScore, 0.28); }
  checks.push({ name: "spatial_freq", score: freqScore, reason_code: freqCode, metrics: { spec_peak_ratio: peak, lattice_ratio: lattice }, note: "2-D FFT lattice / axial peaks." });

  const cv = num(v.noise_cv, num(v.tile_std_cv, 0.2));
  const cs = num(v.center_surround, 1.1);
  let noiseScore = clip01(Math.min(logisticScore(cv, 0.22, 0.85), logisticScore(cs, 1.15, 3.2)));
  let noiseCode = null;
  if (cv > 0.62 || cs > 2.15) { noiseCode = "NOISE_INCONSISTENT"; noiseScore = Math.min(noiseScore, 0.28); }
  checks.push({ name: "noise", score: noiseScore, reason_code: noiseCode, metrics: { noise_cv: cv, center_surround: cs }, note: "Tile residual-std mismatch." });

  const block = num(v.blockiness, num(v.boundary_interior, 1.05));
  let blockScore = logisticScore(block, 1.05, 1.85);
  let blockCode = null;
  if (block > 1.55) { blockCode = "BLOCK_ARTIFACT"; blockScore = Math.min(blockScore, 0.32); }
  checks.push({ name: "block", score: clip01(blockScore), reason_code: blockCode, metrics: { blockiness: block }, note: "8x8 boundary vs interior." });

  const chroma = num(v.chroma_spread, num(v.illuminant_var, 0.001));
  let chromaScore = logisticScore(chroma, 0.0008, 0.012);
  let chromaCode = null;
  if (chroma > 0.0065) { chromaCode = "CHROMA_INCONSISTENT"; chromaScore = Math.min(chromaScore, 0.30); }
  checks.push({ name: "chroma", score: clip01(chromaScore), reason_code: chromaCode, metrics: { chroma_spread: chroma }, note: "Local gray-world illuminant spread." });

  const seam = num(v.seam_frac, 0.15);
  const jump = num(v.color_jump, 0.04);
  let blendScore = clip01(Math.min(logisticScore(seam, 0.18, 0.62), logisticScore(jump, 0.04, 0.28)));
  let blendCode = null;
  if ((seam > 0.42 && jump > 0.10) || seam > 0.72) { blendCode = "BLEND_BOUNDARY"; blendScore = Math.min(blendScore, 0.26); }
  checks.push({ name: "blend", score: blendScore, reason_code: blendCode, metrics: { seam_frac: seam, color_jump: jump }, note: "Hard seam + color jump." });

  const rough = num(v.shade_rough, 2e-6);
  let lightScore = logisticScore(rough, 1.5e-6, 8e-5);
  let lightCode = null;
  if (rough > 4.5e-5) { lightCode = "LIGHTING_INCONSISTENT"; lightScore = Math.min(lightScore, 0.32); }
  checks.push({ name: "lighting", score: clip01(lightScore), reason_code: lightCode, metrics: { shade_rough: rough }, note: "Low-frequency shading roughness." });
  return checks;
}

function temporalChecks(t) {
  t = t || {};
  const checks = [];
  const flick = num(t.flicker, num(t.max_dmean, 0.01));
  let fScore = logisticScore(flick, 0.012, 0.09);
  let fCode = null;
  if (flick > 0.055) { fCode = "TEMPORAL_FLICKER"; fScore = Math.min(fScore, 0.24); }
  checks.push({ name: "flicker", score: clip01(fScore), reason_code: fCode, metrics: { flicker: flick }, note: "Frame-to-frame mean jump." });

  const flow = num(t.flow_rough, num(t.motion, 0.3));
  let mScore = logisticScore(flow, 0.35, 2.2);
  let mCode = null;
  if (flow > 1.55) { mCode = "MOTION_INCONSISTENT"; mScore = Math.min(mScore, 0.28); }
  checks.push({ name: "motion", score: clip01(mScore), reason_code: mCode, metrics: { flow_rough: flow }, note: "Block-flow roughness." });

  const idj = num(t.identity_jump, num(t.still_hist_l1, 0.08));
  let iScore = logisticScore(idj, 0.08, 0.55);
  let iCode = null;
  if (idj > 0.32) { iCode = "IDENTITY_FLICKER"; iScore = Math.min(iScore, 0.26); }
  checks.push({ name: "identity", score: clip01(iScore), reason_code: iCode, metrics: { identity_jump: idj }, note: "Center histogram jump on still pairs." });

  const interp = num(t.rel_residual, 0.5);
  let pScore = logisticScore(interp, 0.55, 0.08);
  let pCode = null;
  if (interp < 0.16) { pCode = "INTERP_ARTIFACT"; pScore = Math.min(pScore, 0.30); }
  checks.push({ name: "interp", score: clip01(pScore), reason_code: pCode, metrics: { rel_residual: interp }, note: "Odd-frame blend residual." });
  return checks;
}

function avCheck(a) {
  a = a || {};
  const corr = num(a.av_corr, num(a.corr, 0.5));
  const delay = Math.abs(num(a.delay_s, 0.02));
  let score = clip01(0.65 * logisticScore(corr, 0.55, 0.05) + 0.35 * logisticScore(delay, 0.04, 0.22));
  let code = null;
  if (corr < 0.12 || delay > 0.16) { code = "AV_SYNC_FAIL"; score = Math.min(score, 0.22); }
  return { name: "av_sync", score, reason_code: code, metrics: { av_corr: corr, delay_s: delay }, note: "Audio RMS vs mouth-proxy motion." };
}

function pitchFromPcm(x, sr) {
  const hop = Math.max(64, Math.round(0.01 * sr));
  const win = Math.max(128, Math.round(0.04 * sr));
  const f0s = [];
  for (let i = 0; i + win <= x.length; i += hop) {
    let bestLag = 0, best = -1;
    const lo = Math.max(1, Math.round(sr / 350));
    const hi = Math.min(win - 2, Math.round(sr / 70));
    for (let lag = lo; lag <= hi; lag++) {
      let s = 0;
      for (let k = 0; k < win - lag; k++) s += x[i + k] * x[i + k + lag];
      if (s > best) { best = s; bestLag = lag; }
    }
    if (bestLag > 0) f0s.push(sr / bestLag);
  }
  if (f0s.length < 4) return { f0_jump: 1.2, f0_cv: 0.04 };
  let maxSt = 0;
  for (let i = 1; i < f0s.length; i++) {
    const st = Math.abs(12 * Math.log2(f0s[i] / f0s[i - 1]));
    if (st > maxSt) maxSt = st;
  }
  const mean = f0s.reduce((a, b) => a + b, 0) / f0s.length;
  let v = 0;
  for (let i = 0; i < f0s.length; i++) v += (f0s[i] - mean) * (f0s[i] - mean);
  return { f0_jump: maxSt, f0_cv: Math.sqrt(v / f0s.length) / (mean + 1e-9) };
}

function combine(checks) {
  const weights = { ...AUDIO_WEIGHTS, ...VISUAL_WEIGHTS, ...TEMPORAL_WEIGHTS, av_sync: AV_WEIGHT };
  let nume = 0, den = 0;
  for (const [name, w] of Object.entries(weights)) {
    const vals = checks.filter((c) => c.name === name).map((c) => c.score);
    if (!vals.length) continue;
    const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
    nume += w * mean;
    den += w;
  }
  let score = clip01(den > 0 ? nume / den : 0);
  const codes = [];
  for (const c of checks) {
    if (c.reason_code && !codes.includes(c.reason_code)) codes.push(c.reason_code);
  }
  const smoking = new Set([
    "FREQ_FINGERPRINT", "NOISE_INCONSISTENT", "BLEND_BOUNDARY", "CHROMA_INCONSISTENT",
    "TEMPORAL_FLICKER", "IDENTITY_FLICKER", "INTERP_ARTIFACT", "PITCH_JUMP",
    "PHASE_SHIFT_UNNATURAL", "AV_SYNC_FAIL",
  ]);
  const nSmoke = codes.filter((c) => smoking.has(c)).length;
  if (nSmoke >= 2) score = Math.min(score, 0.26);
  else if (nSmoke === 1) score = Math.min(score, 0.36);
  let verdict = "inconclusive";
  if (score < 0.42 && codes.length) verdict = "deepfake";
  else if (score >= 0.55) verdict = "consistent";
  return { score, reason_codes: codes, verdict };
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
          summary: "Multi-signal deepfake risk assessment (audio features/PCM + visual + pitch + A/V)",
          requestBody: {
            required: true,
            content: {
              "application/json": {
                schema: {
                  type: "object",
                  properties: {
                    features: { type: "object", properties: { rms: { type: "number" }, zcr: { type: "number" }, f0_jump: { type: "number" } }, additionalProperties: true },
                    visual: { type: "object", additionalProperties: true, description: "Spatial metrics: spec_peak_ratio, noise_cv, blockiness, chroma_spread, seam_frac" },
                    video: { type: "object", additionalProperties: true, description: "Temporal metrics: flicker, flow_rough, identity_jump, rel_residual" },
                    pitch: { type: "object", additionalProperties: true },
                    av: { type: "object", properties: { av_corr: { type: "number" }, delay_s: { type: "number" } } },
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
      "/v1/detect": {
        post: {
          operationId: "vibelockDetect",
          summary: "Same engine as /v1/analyze; deepfake-oriented alias",
          requestBody: { required: true, content: { "application/json": { schema: { type: "object", additionalProperties: true } } } },
          responses: { "200": { description: "Deepfake risk assessment" } },
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
  const visual = (body.visual && typeof body.visual === "object") ? body.visual : (body.image && typeof body.image === "object" ? body.image : null);
  const video = (body.video && typeof body.video === "object") ? body.video : (body.temporal && typeof body.temporal === "object" ? body.temporal : null);
  const av = (body.av && typeof body.av === "object") ? body.av : null;
  const pitchIn = (body.pitch && typeof body.pitch === "object") ? body.pitch : null;
  if (pitchIn && features) Object.assign(features, pitchIn);
  if (!features && !visual && !video && !av) {
    return runtimeJson({ ok: false, error: "provide features:{rms,zcr,...} or pcm_b64+rate and/or visual/video/av", label: LABEL, hosted_mic: false, listen: "local" }, 400);
  }
  const { checks, notes } = features ? checksFromFeatures(features) : { checks: [], notes: [LABEL, HOSTED_NOTE] };
  if (visual) checks.push(...visualChecks(visual));
  if (video) checks.push(...temporalChecks(video));
  if (av) checks.push(avCheck(av));
  const comb = combine(checks);
  if (visual) mode = video || av ? "av" : (features ? "av" : "image");
  else if (video) mode = features ? "av" : "video";
  else if (av) mode = "av";
  const signals = [];
  if (features) signals.push("audio");
  if (visual) signals.push("spatial");
  if (video) signals.push("temporal");
  if (av) signals.push("av_sync");
  return runtimeJson({
    ok: true,
    product: PRODUCT,
    label: LABEL,
    liveness_proof: false,
    hosted_mic: false,
    listen: "local",
    mode,
    engine: "deepfake",
    verdict: comb.verdict,
    score: comb.score,
    reason_codes: comb.reason_codes,
    checks,
    features: features || undefined,
    signals,
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

  if (path === "/v1/skill" && request.method === "GET") {
    return new Response(SKILL_MARKDOWN, {
      status: 200,
      headers: {
        "Content-Type": "text/markdown; charset=utf-8",
        "Cache-Control": "private, no-store",
        "X-KV-Increment": "false",
        "Access-Control-Allow-Origin": "*",
      },
    });
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
    return runtimeJson({ product: PRODUCT, label: LABEL, endpoints: ["GET /v1/health", "POST /v1/analyze", "POST /v1/detect", "GET /openapi.json", "GET /ai"] });
  }
  if ((path === "/v1/analyze" || path === "/v1/detect") && request.method === "POST") {
    let body = {};
    try { body = await readJsonBody(request); } catch (e) { return runtimeJson({ ok: false, error: e.message, label: LABEL }, e.status || 400); }
    return handleAnalyze(body);
  }
  if (path === "/v1/analyze" || path === "/v1/detect") return runtimeJson({ error: "method not allowed" }, 405);
  if (path.startsWith("/v1/")) return runtimeJson({ error: "not found", product: PRODUCT }, 404);
  return null;
}
