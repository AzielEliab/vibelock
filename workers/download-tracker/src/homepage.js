/**
 * VibeLock Worker homepage — product UI (not a downloads shell).
 * Author: Aziel Eliab only.
 */

const HOST = "https://vibelock-download-tracker.vibelock.workers.dev";
const GITHUB_REPO = "https://github.com/AzielEliab/vibelock";
const GITHUB_LATEST = "https://github.com/AzielEliab/vibelock/releases/latest";
const CATALOG = "https://aziel-runtime.vibelock.workers.dev/";
const DEFAULT_ASSET = "vibelock-0.3.0.tar.gz";
const INSTALL_LINE = "curl -fsSL https://vibelock-download-tracker.vibelock.workers.dev/install.sh | bash";
const TITLE = "VibeLock — Aziel Eliab";
const DESCRIPTION =
  "VibeLock by Aziel Eliab is physics + A/V deepfake risk assessment for audio, image, and talking-head sync. Not a lie detector and not courtroom proof.";
const MOTTO = "Sound can be forged. Pixels can be forged. Physics is harder to fake.";
const BANNER =
  "Physics + A/V deepfake detection is a risk assessment, not a lie detector and not courtroom proof. Hosted is not a live microphone. The Worker does not decode pixels on the server — this page extracts limited PCM or visual metrics in your browser, then calls POST /v1/analyze. Full local decode stays on 127.0.0.1 via vibelock ui.";

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function citeDoc() {
  return {
    author: "Aziel Eliab",
    title: "VibeLock",
    one_line: "Physics + A/V deepfake risk assessment. Not a lie detector and not courtroom proof.",
    github: GITHUB_REPO,
    download: HOST + "/download",
    homepage: HOST + "/",
    license: "Apache-2.0",
    catalog: CATALOG,
  };
}

export function llmsTxt() {
  return [
    "# VibeLock",
    "",
    "Author: Aziel Eliab",
    "License: Apache-2.0. Forks welcome.",
    "",
    MOTTO,
    "",
    DESCRIPTION,
    "",
    "Homepage (product UI): " + HOST + "/",
    "Analyze: POST " + HOST + "/v1/analyze",
    "Detect: POST " + HOST + "/v1/detect",
    "Health: GET " + HOST + "/v1/health",
    "OpenAPI: " + HOST + "/openapi.json",
    "Skill: " + HOST + "/v1/skill",
    "AI assistants: ChatGPT (GPT Actions / OpenAI), Grok (xAI), Venice, Claude (Anthropic), Cursor (MCP), Glama (MCP), Perplexity, Microsoft Copilot / Bing, Google Gemini / Vertex, Mistral, Meta AI, Apple Intelligence surfaces, Amazon Q tooling, DuckAssist, You.com, Cohere, and other MCP/OpenAPI-capable assistants.",
    "How to wire: " + HOST + "/ai",
    "MCP: https://aziel-runtime.vibelock.workers.dev/mcp",
    "This Worker MCP pointer: " + HOST + "/mcp",
    "Suite mesh: GET " + HOST + "/v1/mesh (PROXY; default OFF; QNM-BUILD-1.0 live|locked|isolated; QNS-CD-1.0 hub cite / Worker mesh cross-map; no Node Gate; no public qnsd proxy)",
    "Counted download: " + HOST + "/download?asset=" + DEFAULT_ASSET,
    "GitHub: " + GITHUB_REPO,
    "",
    "Identity: Aziel Eliab only.",
    "",
  ].join("\n");
}

export function robotsTxt() {
  return [
    "User-agent: *",
    "Allow: /",
    "Allow: /openapi.json",
    "Allow: /cite.json",
    "Allow: /llms.txt",
    "Allow: /v1/health",
    "Allow: /v1/skill",
    "Allow: /v1/mesh",
    "Allow: /mcp",
    "",
  ].join("\n");
}

function jsonLd() {
  return {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "WebSite",
        name: "VibeLock",
        url: HOST + "/",
        description: DESCRIPTION,
        author: { "@type": "Person", name: "Aziel Eliab", url: GITHUB_REPO },
      },
      {
        "@type": "SoftwareApplication",
        name: "VibeLock",
        applicationCategory: "DeveloperApplication",
        operatingSystem: "Web",
        url: HOST + "/",
        author: { "@type": "Person", name: "Aziel Eliab", url: GITHUB_REPO },
        codeRepository: GITHUB_REPO,
        downloadUrl: HOST + "/download",
        license: "https://www.apache.org/licenses/LICENSE-2.0",
        description: DESCRIPTION,
        isAccessibleForFree: true,
        offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
      },
      {
        "@type": "Person",
        name: "Aziel Eliab",
        url: GITHUB_REPO,
      },
    ],
  };
}

const CLIENT_JS = [
  "(function () {",
  "  var $ = function (id) { return document.getElementById(id); };",
  "  var last = null;",
  "  var installCmd = " + JSON.stringify(INSTALL_LINE) + ";",
  "",
  "  function setText(el, text) { if (el) el.textContent = text; }",
  "  function numOrNull(v) {",
  "    if (v == null || v === '') return null;",
  "    var n = Number(v);",
  "    return Number.isFinite(n) ? n : null;",
  "  }",
  "  function put(obj, key, n) { if (n != null) obj[key] = n; }",
  "  function hasKeys(o) { return o && Object.keys(o).length > 0; }",
  "",
  "  function parseNotes(text) {",
  "    var t = String(text || '').trim();",
  "    if (!t) return {};",
  "    if (t.charAt(0) === '{') {",
  "      try {",
  "        var j = JSON.parse(t);",
  "        return (j && typeof j === 'object' && !Array.isArray(j)) ? j : {};",
  "      } catch (e) {}",
  "    }",
  "    var buckets = { features: {}, visual: {}, video: {}, pitch: {}, av: {} };",
  "    var map = {",
  "      rms: ['features', 'rms'], zcr: ['features', 'zcr'], peak: ['features', 'peak'],",
  "      crest: ['features', 'crest'], centroid: ['features', 'centroid'],",
  "      fine_var: ['features', 'fine_var'], env_jump: ['features', 'env_jump'],",
  "      rms_var: ['features', 'rms_var'], formant_jump_hz: ['features', 'formant_jump_hz'],",
  "      decay_tau_s: ['features', 'decay_tau_s'], buzz_ratio: ['features', 'buzz_ratio'],",
  "      f0_jump: ['pitch', 'f0_jump'], f0_cv: ['pitch', 'f0_cv'],",
  "      blockiness: ['visual', 'blockiness'], noise_cv: ['visual', 'noise_cv'],",
  "      spec_peak_ratio: ['visual', 'spec_peak_ratio'], lattice_ratio: ['visual', 'lattice_ratio'],",
  "      chroma_spread: ['visual', 'chroma_spread'], seam_frac: ['visual', 'seam_frac'],",
  "      color_jump: ['visual', 'color_jump'], shade_rough: ['visual', 'shade_rough'],",
  "      flicker: ['video', 'flicker'], flow_rough: ['video', 'flow_rough'],",
  "      identity_jump: ['video', 'identity_jump'], rel_residual: ['video', 'rel_residual'],",
  "      av_corr: ['av', 'av_corr'], delay_s: ['av', 'delay_s'], corr: ['av', 'corr']",
  "    };",
  "    var lines = t.split(/\\n|;/);",
  "    for (var i = 0; i < lines.length; i++) {",
  "      var line = lines[i].trim();",
  "      if (!line || line.charAt(0) === '#') continue;",
  "      var m = line.match(/^(?:(features|visual|video|pitch|av)\\.)?([a-z0-9_]+)\\s*[:=]\\s*(-?[0-9.eE+-]+)\\s*$/i);",
  "      if (!m) continue;",
  "      var name = m[2].toLowerCase();",
  "      var n = Number(m[3]);",
  "      if (!Number.isFinite(n)) continue;",
  "      var dest = m[1] ? [m[1].toLowerCase(), name] : map[name];",
  "      if (!dest) continue;",
  "      if (!buckets[dest[0]]) buckets[dest[0]] = {};",
  "      buckets[dest[0]][dest[1]] = n;",
  "    }",
  "    var out = {};",
  "    if (hasKeys(buckets.features)) out.features = buckets.features;",
  "    if (hasKeys(buckets.visual)) out.visual = buckets.visual;",
  "    if (hasKeys(buckets.video)) out.video = buckets.video;",
  "    if (hasKeys(buckets.pitch)) out.pitch = buckets.pitch;",
  "    if (hasKeys(buckets.av)) out.av = buckets.av;",
  "    return out;",
  "  }",
  "",
  "  function collectForm() {",
  "    var features = {}, visual = {}, video = {}, pitch = {}, av = {};",
  "    put(features, 'rms', numOrNull($('f-rms').value));",
  "    put(features, 'zcr', numOrNull($('f-zcr').value));",
  "    put(features, 'centroid', numOrNull($('f-centroid').value));",
  "    put(features, 'env_jump', numOrNull($('f-env-jump').value));",
  "    put(features, 'formant_jump_hz', numOrNull($('f-formant').value));",
  "    put(pitch, 'f0_jump', numOrNull($('f-f0-jump').value));",
  "    put(pitch, 'f0_cv', numOrNull($('f-f0-cv').value));",
  "    put(visual, 'blockiness', numOrNull($('v-block').value));",
  "    put(visual, 'noise_cv', numOrNull($('v-noise').value));",
  "    put(visual, 'spec_peak_ratio', numOrNull($('v-peak').value));",
  "    put(visual, 'chroma_spread', numOrNull($('v-chroma').value));",
  "    put(visual, 'seam_frac', numOrNull($('v-seam').value));",
  "    put(video, 'flicker', numOrNull($('t-flicker').value));",
  "    put(video, 'flow_rough', numOrNull($('t-flow').value));",
  "    put(video, 'identity_jump', numOrNull($('t-id').value));",
  "    put(av, 'av_corr', numOrNull($('a-corr').value));",
  "    put(av, 'delay_s', numOrNull($('a-delay').value));",
  "    var body = parseNotes($('notes').value);",
  "    if (hasKeys(features)) body.features = Object.assign({}, body.features || {}, features);",
  "    if (hasKeys(visual)) body.visual = Object.assign({}, body.visual || {}, visual);",
  "    if (hasKeys(video)) body.video = Object.assign({}, body.video || {}, video);",
  "    if (hasKeys(pitch)) body.pitch = Object.assign({}, body.pitch || {}, pitch);",
  "    if (hasKeys(av)) body.av = Object.assign({}, body.av || {}, av);",
  "    var rate = numOrNull($('f-rate').value);",
  "    if (rate) body.rate = rate;",
  "    return body;",
  "  }",
  "",
  "  function bytesToB64(bytes) {",
  "    var chunk = 0x8000;",
  "    var s = '';",
  "    for (var i = 0; i < bytes.length; i += chunk) {",
  "      s += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));",
  "    }",
  "    return btoa(s);",
  "  }",
  "",
  "  function floatToPcmB64(samples) {",
  "    var n = Math.min(samples.length, 32000);",
  "    var out = new Uint8Array(n * 2);",
  "    var view = new DataView(out.buffer);",
  "    for (var i = 0; i < n; i++) {",
  "      var x = samples[i];",
  "      if (x > 1) x = 1;",
  "      if (x < -1) x = -1;",
  "      view.setInt16(i * 2, x < 0 ? (x * 0x8000) : (x * 0x7fff), true);",
  "    }",
  "    return bytesToB64(out);",
  "  }",
  "",
  "  function visualFromImageData(img) {",
  "    var d = img.data, w = img.width, h = img.height;",
  "    var luma = new Float64Array(w * h);",
  "    var i, x, y;",
  "    for (i = 0; i < w * h; i++) {",
  "      var o = i * 4;",
  "      luma[i] = 0.2126 * d[o] + 0.7152 * d[o + 1] + 0.0722 * d[o + 2];",
  "    }",
  "    var bEdge = 0, bInt = 0, nE = 0, nI = 0;",
  "    for (y = 0; y < h; y++) {",
  "      for (x = 0; x + 1 < w; x++) {",
  "        var dx = Math.abs(luma[y * w + x] - luma[y * w + x + 1]);",
  "        if (x % 8 === 7) { bEdge += dx; nE++; } else { bInt += dx; nI++; }",
  "      }",
  "    }",
  "    var meanE = bEdge / Math.max(1, nE);",
  "    var meanI = bInt / Math.max(1, nI);",
  "    var blockiness = meanI > 1e-6 ? meanE / meanI : 1.05;",
  "    var tile = 16;",
  "    var stds = [];",
  "    for (y = 0; y + tile <= h; y += tile) {",
  "      for (x = 0; x + tile <= w; x += tile) {",
  "        var s = 0, s2 = 0, n = 0, yy, xx;",
  "        for (yy = 0; yy < tile; yy++) {",
  "          for (xx = 0; xx < tile; xx++) {",
  "            var v = luma[(y + yy) * w + (x + xx)];",
  "            s += v; s2 += v * v; n++;",
  "          }",
  "        }",
  "        var mean = s / n;",
  "        stds.push(Math.sqrt(Math.max(0, s2 / n - mean * mean)));",
  "      }",
  "    }",
  "    var m = 0;",
  "    for (i = 0; i < stds.length; i++) m += stds[i];",
  "    m = m / Math.max(1, stds.length);",
  "    var vr = 0;",
  "    for (i = 0; i < stds.length; i++) vr += (stds[i] - m) * (stds[i] - m);",
  "    var noise_cv = m > 1e-6 ? Math.sqrt(vr / Math.max(1, stds.length)) / m : 0.2;",
  "    var cell = 32;",
  "    var illuminants = [];",
  "    for (y = 0; y + cell <= h; y += cell) {",
  "      for (x = 0; x + cell <= w; x += cell) {",
  "        var sr = 0, sg = 0, sb = 0, nn = 0, yy, xx;",
  "        for (yy = 0; yy < cell; yy++) {",
  "          for (xx = 0; xx < cell; xx++) {",
  "            var p = ((y + yy) * w + (x + xx)) * 4;",
  "            sr += d[p]; sg += d[p + 1]; sb += d[p + 2]; nn++;",
  "          }",
  "        }",
  "        var gr = (sr + sg + sb) / (3 * nn) + 1e-6;",
  "        illuminants.push([sr / nn / gr, sg / nn / gr, sb / nn / gr]);",
  "      }",
  "    }",
  "    var mr = 0, mg = 0, mb = 0;",
  "    for (i = 0; i < illuminants.length; i++) { mr += illuminants[i][0]; mg += illuminants[i][1]; mb += illuminants[i][2]; }",
  "    var il = Math.max(1, illuminants.length);",
  "    mr /= il; mg /= il; mb /= il;",
  "    var ch = 0;",
  "    for (i = 0; i < illuminants.length; i++) {",
  "      var dr = illuminants[i][0] - mr, dg = illuminants[i][1] - mg, db = illuminants[i][2] - mb;",
  "      ch += dr * dr + dg * dg + db * db;",
  "    }",
  "    var chroma_spread = ch / Math.max(1, illuminants.length);",
  "    var seams = 0, tot = 0;",
  "    for (y = 1; y < h - 1; y++) {",
  "      for (x = 1; x < w - 1; x++) {",
  "        var g = Math.abs(luma[y * w + x] - luma[y * w + x - 1]) + Math.abs(luma[y * w + x] - luma[(y - 1) * w + x]);",
  "        tot++;",
  "        if (g > 28) seams++;",
  "      }",
  "    }",
  "    return {",
  "      blockiness: blockiness,",
  "      noise_cv: noise_cv,",
  "      chroma_spread: chroma_spread,",
  "      seam_frac: tot ? seams / tot : 0.15,",
  "      spec_peak_ratio: 3.0",
  "    };",
  "  }",
  "",
  "  function fileToAnalyze(file) {",
  "    return new Promise(function (resolve, reject) {",
  "      var name = String(file.name || '').toLowerCase();",
  "      var type = String(file.type || '').toLowerCase();",
  "      var isImage = type.indexOf('image/') === 0 || /\\.(png|jpe?g|gif|webp|bmp|ppm)$/.test(name);",
  "      var isAudio = type.indexOf('audio/') === 0 || /\\.(wav|wave|flac|mp3|ogg|m4a)$/.test(name);",
  "      if (isImage) {",
  "        var url = URL.createObjectURL(file);",
  "        var img = new Image();",
  "        img.onload = function () {",
  "          var canvas = document.createElement('canvas');",
  "          var max = 256;",
  "          var scale = Math.min(1, max / Math.max(img.width, img.height));",
  "          canvas.width = Math.max(8, Math.round(img.width * scale));",
  "          canvas.height = Math.max(8, Math.round(img.height * scale));",
  "          var ctx = canvas.getContext('2d');",
  "          ctx.drawImage(img, 0, 0, canvas.width, canvas.height);",
  "          URL.revokeObjectURL(url);",
  "          resolve({ visual: visualFromImageData(ctx.getImageData(0, 0, canvas.width, canvas.height)) });",
  "        };",
  "        img.onerror = function () { URL.revokeObjectURL(url); reject(new Error('Could not read that image in the browser.')); };",
  "        img.src = url;",
  "        return;",
  "      }",
  "      if (isAudio) {",
  "        var reader = new FileReader();",
  "        reader.onload = function () {",
  "          var Ctx = window.AudioContext || window.webkitAudioContext;",
  "          if (!Ctx) { reject(new Error('This browser cannot decode audio. Paste features or use vibelock ui locally.')); return; }",
  "          var ctx = new Ctx();",
  "          ctx.decodeAudioData(reader.result.slice(0), function (buf) {",
  "            var ch = buf.getChannelData(0);",
  "            var rate = buf.sampleRate || 16000;",
  "            resolve({ pcm_b64: floatToPcmB64(ch), rate: rate, pcm_dtype: 'int16' });",
  "            ctx.close && ctx.close();",
  "          }, function () { reject(new Error('Could not decode that audio. Try WAV, or paste features.')); });",
  "        };",
  "        reader.onerror = function () { reject(new Error('Could not read that file.')); };",
  "        reader.readAsArrayBuffer(file);",
  "        return;",
  "      }",
  "      reject(new Error('Use a WAV/audio file or a still image, or fill the feature fields.'));",
  "    });",
  "  }",
  "",
  "  function fail(msg) {",
  "    var err = $('err');",
  "    err.hidden = false;",
  "    setText(err, msg);",
  "  }",
  "",
  "  function show(data) {",
  "    last = data;",
  "    $('err').hidden = true;",
  "    $('result').hidden = false;",
  "    var score = Number(data.score);",
  "    if (!Number.isFinite(score)) score = 0;",
  "    var verdict = String(data.verdict || 'inconclusive');",
  "    var plain = data.plain_sentence || (verdict === 'consistent'",
  "      ? 'This media looks consistent with a real voice or camera — still only a risk score.'",
  "      : (verdict === 'deepfake'",
  "        ? 'This media looks inconsistent — higher deepfake risk. Not a lie detector.'",
  "        : 'This run is inconclusive. Risk assessment, not courtroom proof.'));",
  "    setText($('score'), score.toFixed(3));",
  "    setText($('score-pct'), Math.round(score * 100) + '%');",
  "    setText($('verdict'), verdict);",
  "    $('verdict').className = 'pill ' + (verdict === 'consistent' ? 'yes' : (verdict === 'deepfake' ? 'no' : 'review'));",
  "    setText($('mode'), (data.mode || '') + (data.engine ? ' · ' + data.engine : ''));",
  "    setText($('signals'), (data.signals && data.signals.length) ? data.signals.join(' · ') : '—');",
  "    setText($('plain'), plain);",
  "    $('plain').className = 'plain ' + (verdict === 'consistent' ? 'ok' : 'bad');",
  "    $('bar').style.width = Math.max(0, Math.min(100, Math.round(score * 100))) + '%';",
  "    setText($('limit-again'), data.limitation || data.label || " + JSON.stringify(BANNER.split('.')[0] + ".") + ");",
  "    var codes = data.reason_codes || [];",
  "    var box = $('codes');",
  "    box.textContent = '';",
  "    if (!codes.length) {",
  "      var none = document.createElement('span');",
  "      none.className = 'code ok';",
  "      none.textContent = 'no reason codes';",
  "      box.appendChild(none);",
  "    } else {",
  "      codes.forEach(function (c) {",
  "        var el = document.createElement('span');",
  "        el.className = 'code';",
  "        el.textContent = c;",
  "        box.appendChild(el);",
  "      });",
  "    }",
  "    var ul = $('checks');",
  "    ul.textContent = '';",
  "    (data.checks || []).forEach(function (ch) {",
  "      var li = document.createElement('li');",
  "      var left = document.createElement('span');",
  "      left.textContent = ch.name + (ch.reason_code ? '  [' + ch.reason_code + ']' : '');",
  "      var right = document.createElement('span');",
  "      right.textContent = Number(ch.score).toFixed(3);",
  "      li.appendChild(left);",
  "      li.appendChild(right);",
  "      ul.appendChild(li);",
  "    });",
  "    var notes = Array.isArray(data.notes) ? data.notes.join(' ') : '';",
  "    setText($('notes-out'), notes);",
  "  }",
  "",
  "  async function postAnalyze(body) {",
  "    var res = await fetch('/v1/analyze', {",
  "      method: 'POST',",
  "      headers: { 'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0' },",
  "      body: JSON.stringify(body)",
  "    });",
  "    var data = await res.json();",
  "    if (!res.ok || data.ok === false) throw new Error(data.error || ('HTTP ' + res.status));",
  "    return data;",
  "  }",
  "",
  "  async function run(body) {",
  "    $('analyze-btn').disabled = true;",
  "    try {",
  "      if (!body.features && !body.visual && !body.video && !body.av && !body.pcm_b64 && !body.pitch) {",
  "        throw new Error('Paste notes, fill a field, upload a file, or tap a sample.');",
  "      }",
  "      show(await postAnalyze(body));",
  "    } catch (e) { fail(String(e.message || e)); }",
  "    finally { $('analyze-btn').disabled = false; }",
  "  }",
  "",
  "  function preset(kind) {",
  "    if (kind === 'tone') {",
  "      return { features: { rms: 0.10, zcr: 0.08, centroid: 0.42, env_jump: 0.25 }, pitch: { f0_jump: 1.2, f0_cv: 0.04 } };",
  "    }",
  "    if (kind === 'photo') {",
  "      return { visual: { blockiness: 1.08, noise_cv: 0.18, spec_peak_ratio: 3.1, chroma_spread: 0.0009, seam_frac: 0.12 } };",
  "    }",
  "    return {",
  "      features: { rms: 0.08, zcr: 0.07 },",
  "      visual: { blockiness: 1.8, noise_cv: 0.7, spec_peak_ratio: 9.2, seam_frac: 0.48, chroma_spread: 0.008 },",
  "      pitch: { f0_jump: 8.5 },",
  "      video: { flicker: 0.07, identity_jump: 0.40 },",
  "      av: { av_corr: 0.08, delay_s: 0.20 }",
  "    };",
  "  }",
  "",
  "  $('analyze-form').addEventListener('submit', function (ev) {",
  "    ev.preventDefault();",
  "    var body = collectForm();",
  "    var file = $('media').files[0];",
  "    if (file) {",
  "      $('analyze-btn').disabled = true;",
  "      fileToAnalyze(file).then(function (extra) {",
  "        run(Object.assign(body, extra));",
  "      }).catch(function (e) {",
  "        $('analyze-btn').disabled = false;",
  "        fail(String(e.message || e));",
  "      });",
  "      return;",
  "    }",
  "    run(body);",
  "  });",
  "  $('sample-tone').onclick = function () { run(preset('tone')); };",
  "  $('sample-photo').onclick = function () { run(preset('photo')); };",
  "  $('sample-fake').onclick = function () { run(preset('fake')); };",
  "  $('export').onclick = function () {",
  "    if (!last) { fail('Run an analysis first, then export.'); return; }",
  "    var blob = new Blob([JSON.stringify(last, null, 2)], { type: 'application/json' });",
  "    var a = document.createElement('a');",
  "    a.href = URL.createObjectURL(blob);",
  "    a.download = 'vibelock-report.json';",
  "    a.click();",
  "    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);",
  "  };",
  "  var btn = $('install-btn');",
  "  var pre = $('install-cmd');",
  "  if (btn) {",
  "    btn.addEventListener('click', function () {",
  "      function done(ok) {",
  "        btn.textContent = ok ? 'Copied! Paste in Terminal, then run vibelock ui' : 'Select the command, copy it, then run vibelock ui';",
  "        btn.classList.add('copied');",
  "      }",
  "      if (navigator.clipboard && navigator.clipboard.writeText) {",
  "        navigator.clipboard.writeText(installCmd).then(function () { done(true); }).catch(function () { done(false); });",
  "      } else {",
  "        done(false);",
  "        if (pre && window.getSelection) {",
  "          var r = document.createRange();",
  "          r.selectNodeContents(pre);",
  "          var sel = window.getSelection();",
  "          sel.removeAllRanges();",
  "          sel.addRange(r);",
  "        }",
  "      }",
  "    });",
  "  }",
  "  function meshNum() {",
  "    for (var i = 0; i < arguments.length; i++) {",
  "      var raw = arguments[i];",
  "      if (raw == null || raw === '') continue;",
  "      var n = typeof raw === 'number' ? raw : Number(String(raw).replace(/,/g, ''));",
  "      if (Number.isFinite(n) && n >= 0) return Math.floor(n);",
  "    }",
  "    return 0;",
  "  }",
  "  function unwrapMesh(j) {",
  "    if (!j || typeof j !== 'object') return {};",
  "    if (j.result && typeof j.result === 'object') return Object.assign({}, j, j.result);",
  "    if (j.mesh && typeof j.mesh === 'object') return Object.assign({}, j, j.mesh);",
  "    return j;",
  "  }",
  "  function paintMesh(raw) {",
  "    var j = unwrapMesh(raw);",
  "    var on = j.enabled === true || j.enabled === 1 || String(j.status || '').toLowerCase() === 'on';",
  "    var r = (j.rollup && typeof j.rollup === 'object') ? j.rollup : {};",
  "    var live = on ? meshNum(r.live, j.live_nodes, j.live) : 0;",
  "    var locked = on ? meshNum(r.locked, j.locked_nodes, j.locked) : 0;",
  "    var isolated = on ? meshNum(r.isolated, j.isolated_nodes, j.isolated) : 0;",
  "    setText($('meshLiveCount'), String(live));",
  "    setText($('qnmLive'), String(live));",
  "    setText($('qnmLocked'), String(locked));",
  "    setText($('qnmIsolated'), String(isolated));",
  "    var line = $('meshLine');",
  "    if (on) setText(line, 'Suite mesh: on · live ' + live + ' · locked ' + locked + ' · isolated ' + isolated + '. Not an anonymity network.');",
  "    else if (j.status === 'unavailable' || (j.ok === false && j.error)) setText(line, 'Suite mesh: off (unavailable). QNM-BUILD-1.0. QNS-CD-1.0 hub cite. Not an anonymity network.');",
  "    else setText(line, 'Suite mesh: off (default). QNM-BUILD-1.0. QNS-CD-1.0 hub cite. Not an anonymity network.');",
  "    var products = j.products_present || j.products || [];",
  "    var names = Array.isArray(products) ? products.map(function (p) { return typeof p === 'string' ? p : (p && (p.product || p.slug)) || ''; }).filter(Boolean) : [];",
  "    var nodes = Array.isArray(j.nodes) ? j.nodes : [];",
  "    var extra = names.length ? ' · products ' + names.join(', ') : (nodes.length ? ' · ' + nodes.length + ' node labels' : '');",
  "    setText($('meshProducts'), 'Catalog MCP mesh_* · FragGate slug=mesh · /v1/mesh/* PROXY · QNS-CD-1.0 hub cite · not AnonBroadcast · not AZMail ring · not a Node Gate · no public qnsd proxy' + extra);",
  "  }",
  "  async function meshGet(path) {",
  "    var r = await fetch(path, { headers: { 'user-agent': 'Mozilla/5.0', accept: 'application/json' } });",
  "    return r.json();",
  "  }",
  "  async function meshPost(path, payload) {",
  "    var r = await fetch(path, { method: 'POST', headers: { 'content-type': 'application/json', 'user-agent': 'Mozilla/5.0' }, body: JSON.stringify(payload || {}) });",
  "    return r.json();",
  "  }",
  "  async function refreshMesh() {",
  "    try {",
  "      var status = await meshGet('/v1/mesh');",
  "      var merged = status;",
  "      var inner = unwrapMesh(status);",
  "      var on = inner.enabled === true;",
  "      if (on) {",
  "        try {",
  "          var nodes = await meshGet('/v1/mesh/nodes');",
  "          merged = Object.assign({}, inner, unwrapMesh(nodes));",
  "        } catch (e) { /* status is enough */ }",
  "      }",
  "      paintMesh(merged);",
  "      var nodeId = sessionStorage.getItem('vibelock_mesh_node');",
  "      if (on && nodeId) {",
  "        try { await meshPost('/v1/mesh/heartbeat', { node_id: nodeId }); } catch (e) { /* no auto-heal */ }",
  "      }",
  "    } catch (e) {",
  "      paintMesh({ ok: false, enabled: false, status: 'unavailable', error: 'mesh_unavailable' });",
  "    }",
  "  }",
  "  if ($('meshEnable')) {",
  "    $('meshEnable').onclick = async function () {",
  "      var bearer = (($('meshBearer') && $('meshBearer').value) || '').trim();",
  "      paintMesh(await meshPost('/v1/mesh/enable', bearer ? { bearer: bearer } : {}));",
  "      refreshMesh();",
  "    };",
  "  }",
  "  if ($('meshDisable')) {",
  "    $('meshDisable').onclick = async function () {",
  "      sessionStorage.removeItem('vibelock_mesh_node');",
  "      paintMesh(await meshPost('/v1/mesh/disable', {}));",
  "      refreshMesh();",
  "    };",
  "  }",
  "  if ($('meshJoin')) {",
  "    $('meshJoin').onclick = async function () {",
  "      var j = await meshPost('/v1/mesh/join', { product: 'vibelock', label: 'VibeLock Worker' });",
  "      var inner = unwrapMesh(j);",
  "      var id = inner.node_id || inner.id || (inner.session && inner.session.node_id);",
  "      if (id) sessionStorage.setItem('vibelock_mesh_node', String(id));",
  "      paintMesh(j);",
  "      refreshMesh();",
  "    };",
  "  }",
  "  if ($('meshLeave')) {",
  "    $('meshLeave').onclick = async function () {",
  "      var id = sessionStorage.getItem('vibelock_mesh_node');",
  "      if (id) await meshPost('/v1/mesh/leave', { node_id: id });",
  "      sessionStorage.removeItem('vibelock_mesh_node');",
  "      refreshMesh();",
  "    };",
  "  }",
  "  function paintOs() {",
  "    var el = $('os-line');",
  "    if (!el) return;",
  "    var ua = navigator.userAgent || '';",
  "    var plat = navigator.platform || '';",
  "    try {",
  "      if (navigator.userAgentData && navigator.userAgentData.platform) plat = navigator.userAgentData.platform;",
  "    } catch (e) {}",
  "    var phone = '';",
  "    var name = '';",
  "    if (/android/i.test(ua)) phone = 'Android';",
  "    else if (/iPhone|iPad|iPod/i.test(ua)) phone = 'iPhone or iPad';",
  "    else if (/Win/i.test(plat) || /Windows/i.test(ua)) name = 'Windows';",
  "    else if (/Mac/i.test(plat) || /Macintosh|Mac OS/i.test(ua)) name = 'macOS';",
  "    else if (/Linux|X11|CrOS/i.test(plat) || /Linux/i.test(ua)) name = 'Linux';",
  "    if (phone) {",
  "      el.textContent = 'Detected ' + phone + '. The download is a Python package for a computer, not a phone install.';",
  "      return;",
  "    }",
  "    if (name === 'Windows') {",
  "      el.textContent = 'Detected Windows. The download is the Python package. The Terminal command is for macOS and Linux.';",
  "      return;",
  "    }",
  "    if (name) el.textContent = 'Detected ' + name + '. One Python package. One-click install runs the Terminal command.';",
  "  }",
  "  paintOs();",
  "  window.addEventListener('pagehide', function () {",
  "    var id = sessionStorage.getItem('vibelock_mesh_node');",
  "    if (!id || typeof navigator.sendBeacon !== 'function') return;",
  "    try { navigator.sendBeacon('/v1/mesh/leave', new Blob([JSON.stringify({ node_id: id })], { type: 'application/json' })); } catch (e) { /* leave expires in 5 minutes */ }",
  "  });",
  "  refreshMesh();",
  "  setInterval(refreshMesh, 30000);",
  "  document.addEventListener('visibilitychange', function () { if (!document.hidden) refreshMesh(); });",
  "})();",
].join("\n");

export function indexHtml(stats) {
  const downloads = Number(stats.downloads != null ? stats.downloads : stats.total) || 0;
  const views = Number(stats.views) || 0;
  const uses = Number(stats.uses) || 0;
  const gh = stats.github || {};
  const v = views.toLocaleString("en-US");
  const n = downloads.toLocaleString("en-US");
  const u = uses.toLocaleString("en-US");
  const breakdown = (stats.breakdown || [])
    .map(
      (b) =>
        `<li><code>${escapeHtml(b.owner)}/${escapeHtml(b.repo)}</code> branch <code>${escapeHtml(b.branch)}</code> fork=${escapeHtml(b.fork)} → ${escapeHtml(b.count)}</li>`,
    )
    .join("") || "<li>none yet</li>";
  const ld = JSON.stringify(jsonLd());
  const stars = Number(gh.stars) || 0;
  const forks = Number(gh.forks) || 0;
  const watchers = Number(gh.watchers) || 0;
  const rel = Number(gh.release_download_count) || 0;
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${TITLE}</title>
<meta name="description" content="${escapeHtml(DESCRIPTION)}">
<meta name="author" content="Aziel Eliab">
<meta name="robots" content="index,follow">
<meta name="googlebot" content="index,follow">
<link rel="canonical" href="${HOST}/">
<link rel="icon" href="/sigil.png" type="image/png">
<link rel="alternate" href="/cite.json" type="application/json" title="Citation">
<link rel="alternate" href="/llms.txt" type="text/plain" title="llms.txt">
<meta property="og:title" content="${TITLE}">
<meta property="og:description" content="${escapeHtml(DESCRIPTION)}">
<meta property="og:url" content="${HOST}/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="VibeLock">
<meta property="og:image" content="${HOST}/sigil.png">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="${TITLE}">
<meta name="twitter:description" content="${escapeHtml(DESCRIPTION)}">
<meta name="twitter:image" content="${HOST}/sigil.png">
<meta name="color-scheme" content="dark light">
<meta name="theme-color" content="#14110d" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#fbf7f1" media="(prefers-color-scheme: light)">
<script type="application/ld+json">${ld}</script>
<style>
:root {
  color-scheme: dark;
  --bg: #14110d;
  --ink: #f6efe4;
  --muted: #c4b49a;
  --gold: #e7c56a;
  --panel: #1e1a15;
  --line: #8a7860;
  --focus: #f2d48a;
  --yes: #9ee0b8;
  --on-yes: #102117;
  --no: #ffb4b0;
  --rev: #f0d08a;
  --btn: #f4ecdf;
  --btn-ink: #1a1408;
  --field: #120f0c;
  --note-bg: #2a2218;
  --note-ink: #f6e7c8;
  --shadow: 0 18px 48px #00000088;
}
@media (prefers-color-scheme: dark) {
  :root { color-scheme: dark; }
}
@media (prefers-color-scheme: light) {
  :root {
    color-scheme: light;
    --bg: #fbf7f1;
    --ink: #1c1610;
    --muted: #5c5146;
    --gold: #7a5a10;
    --panel: #ffffff;
    --line: #7d7268;
    --focus: #6b4e08;
    --yes: #0f6b3c;
    --on-yes: #fbf7f1;
    --no: #9d1c1c;
    --rev: #7a4e00;
    --btn: #1c1610;
    --btn-ink: #fbf7f1;
    --field: #ffffff;
    --note-bg: #f3ead6;
    --note-ink: #3d3118;
    --shadow: 0 16px 40px #1c161014;
  }
}
* { box-sizing: border-box; }
html, body { background: var(--bg); color: var(--ink); margin: 0; }
body { font: 16px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
img { max-width: 100%; }
a { color: var(--gold); }
a:hover { text-decoration-thickness: 2px; }
:focus { outline: none; }
:focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; }
.skip {
  position: absolute; left: 0.75rem; top: 0.75rem; transform: translateY(-160%);
  background: var(--btn); color: var(--btn-ink); padding: 0.65rem 0.9rem;
  border-radius: 10px; z-index: 5; text-decoration: none; font-weight: 750;
}
.skip:focus, .skip:focus-visible { transform: none; }
.wrap { max-width: 64rem; margin: 0 auto; padding: 1.15rem 1rem 3rem; }
.wrap, main, .hero, .hero-grid, .hero-grid > * { min-width: 0; }
.hero-grid { display: grid; gap: 1.35rem; align-items: center; }
.brandrow { display: flex; align-items: center; gap: 0.75rem; margin: 0 0 1rem; }
.brandmark { width: 40px; height: 40px; border-radius: 10px; object-fit: cover; flex: 0 0 auto; box-shadow: 0 0 0 1px #d4af3755; }
.stamp { margin: 0; color: var(--muted); font-size: 0.95rem; }
h1 { font-size: clamp(2.7rem, 10vw, 4.5rem); line-height: 0.95; letter-spacing: -0.04em; font-weight: 760; margin: 0 0 0.75rem; }
.motto { font-size: clamp(1.12rem, 2.6vw, 1.4rem); line-height: 1.35; margin: 0 0 0.55rem; max-width: 20em; font-weight: 560; }
.lede { color: var(--muted); margin: 0 0 1.15rem; max-width: 36rem; }
.hero-actions { display: flex; flex-direction: column; gap: 0.65rem; margin: 0 0 0.7rem; }
a.btn, button.btn, button {
  font: inherit; cursor: pointer; border-radius: 14px; min-height: 44px;
}
a.btn.primary {
  background: var(--btn); color: var(--btn-ink); font-size: 1.15rem; font-weight: 760;
  padding: 0.95rem 1.45rem; min-height: 3.45rem; text-decoration: none;
  display: inline-flex; align-items: center; justify-content: center;
  box-shadow: var(--shadow); border: 0; width: 100%;
}
button.btn.ghost, button.ghost {
  background: transparent; color: var(--ink); border: 1px solid var(--line);
  padding: 0.8rem 1.05rem; font-weight: 650; min-height: 3.15rem; width: 100%;
}
button.copied { background: var(--yes); color: var(--on-yes); border-color: transparent; }
button:disabled { opacity: 0.55; cursor: wait; }
.os { color: var(--muted); margin: 0 0 0.55rem; font-size: 0.95rem; }
.limit {
  color: var(--note-ink); background: var(--note-bg); border: 1px solid var(--line);
  border-radius: 12px; padding: 0.75rem 0.9rem; margin: 0.85rem 0 0; font-size: 0.95rem;
}
pre, code { font-family: ui-monospace, Menlo, Consolas, monospace; }
pre {
  background: var(--field); color: var(--ink); border: 1px solid var(--line);
  border-radius: 12px; padding: 0.75rem 0.85rem; overflow: auto; font-size: 0.8rem;
  margin: 0.15rem 0 0; max-width: 100%; white-space: pre-wrap; overflow-wrap: anywhere;
}
nav.toc { display: flex; flex-wrap: wrap; gap: 0.45rem; margin: 1.15rem 0 0; }
nav.toc a {
  text-decoration: none; color: var(--ink); border: 1px solid var(--line);
  background: var(--panel); border-radius: 999px; padding: 0.45rem 0.8rem;
  min-height: 44px; display: inline-flex; align-items: center; font-size: 0.92rem;
}
.markplate {
  margin: 0; background: var(--panel); border: 1px solid var(--line); border-radius: 22px;
  padding: 1.15rem 1.15rem 1.05rem; box-shadow: var(--shadow);
}
.stage-top { display: flex; align-items: center; gap: 0.6rem; font-weight: 700; margin-bottom: 0.35rem; }
.stage-top img { width: 28px; height: 28px; border-radius: 8px; box-shadow: 0 0 0 1px #d4af3755; }
.markplate ol { list-style: none; padding: 0; margin: 0.35rem 0 0.7rem; }
.markplate li { display: flex; gap: 0.7rem; align-items: flex-start; margin: 0.55rem 0; }
.markplate li b {
  flex: 0 0 auto; width: 1.7rem; height: 1.7rem; border-radius: 999px;
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--btn); color: var(--btn-ink); font-size: 0.78rem;
}
.markplate figcaption { color: var(--muted); font-size: 0.9rem; margin: 0; }
.block { margin: 1.75rem 0 0; }
h2 { font-size: 1.28rem; letter-spacing: -0.02em; margin: 0 0 0.75rem; }
h3 { font-size: 1.02rem; margin: 0 0 0.28rem; }
.features { list-style: none; padding: 0; margin: 0; display: grid; gap: 0.75rem; }
.features li { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 0.95rem 1rem 1rem; }
.features p, p.help, .meta { color: var(--muted); }
.features p { margin: 0; font-size: 0.95rem; }
.card, .answer, .cite {
  background: var(--panel); border: 1px solid var(--line); border-radius: 16px; padding: 1.05rem 1rem 1.15rem;
}
p.help { margin: 0 0 0.9rem; font-size: 0.95rem; }
label { display: block; font-size: 0.82rem; color: var(--muted); margin: 0.55rem 0 0.25rem; }
textarea, input[type=number], input[type=file], input[type=text] {
  width: 100%; background: var(--field); color: var(--ink); border: 1px solid var(--line);
  border-radius: 10px; padding: 0.65rem 0.75rem; font: inherit;
}
textarea { min-height: 7rem; resize: vertical; }
::placeholder { color: var(--muted); opacity: 1; }
.grid { display: grid; grid-template-columns: 1fr; gap: 0.35rem 0.8rem; }
details { margin: 0.8rem 0; }
details summary { cursor: pointer; color: var(--gold); font-weight: 650; min-height: 44px; display: flex; align-items: center; }
.actions { display: flex; flex-direction: column; gap: 0.55rem; margin: 0.9rem 0 0; }
#analyze-btn {
  background: var(--btn); color: var(--btn-ink); border: 0; font-weight: 750;
  padding: 0.75rem 1.1rem; min-height: 48px;
}
.score-wrap { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.8rem; margin: 0.2rem 0 0.5rem; }
.score { font-size: 2.4rem; font-weight: 780; letter-spacing: -0.03em; font-variant-numeric: tabular-nums; }
.score-pct { font-size: 1.25rem; color: var(--gold); font-weight: 750; }
.mode, .signals { color: var(--muted); font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 0.85rem; }
.plain { font-size: 1.15rem; margin: 0.35rem 0 0.7rem; }
.plain.ok { color: var(--yes); }
.plain.bad { color: var(--rev); }
.bar { height: 8px; background: var(--field); border-radius: 99px; overflow: hidden; border: 1px solid var(--line); }
.bar > span { display: block; height: 100%; background: var(--gold); }
.pill { border-radius: 999px; padding: 0.35rem 0.7rem; font-size: 0.82rem; font-weight: 700; border: 1px solid var(--line); color: var(--ink); }
.pill.yes { color: var(--yes); border-color: var(--yes); }
.pill.no { color: var(--no); border-color: var(--no); }
.pill.review { color: var(--rev); border-color: var(--rev); }
.codes { display: flex; flex-wrap: wrap; gap: 0.35rem; margin: 0.8rem 0; }
.code { font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 0.75rem; padding: 0.2rem 0.45rem; border-radius: 4px; border: 1px solid var(--line); color: var(--rev); }
.code.ok { color: var(--yes); }
.checks { list-style: none; padding: 0; margin: 0.5rem 0 0; }
.checks li { display: flex; justify-content: space-between; gap: 1rem; font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 0.8rem; padding: 0.28rem 0; border-bottom: 1px solid var(--line); }
.err { color: var(--no); margin: 0.6rem 0 0; }
.quiet-counts { display: flex; flex-wrap: wrap; gap: 0.35rem 1rem; margin: 0 0 0.7rem; font-variant-numeric: tabular-nums; }
.quiet-counts b { font-size: 1.25rem; }
.meta { font-size: 0.92rem; }
.counts ul { padding-left: 1.1rem; color: var(--muted); }
.counts li { margin: 0.25rem 0; }
#meshStrip {
  border: 1px solid var(--line); border-radius: 16px; padding: 0.9rem 1rem;
  background: var(--panel); margin: 1.75rem 0 0; display: flex; flex-wrap: wrap;
  align-items: center; gap: 0.65rem 0.9rem; font-size: 0.9rem; color: var(--muted);
}
#meshStrip .live { color: var(--ink); }
#meshStrip .live b { color: var(--gold); font-size: 1.35rem; margin-right: 0.3rem; }
#meshStrip .rollup b { color: var(--gold); }
#meshStrip button {
  font: 650 0.82rem/1 system-ui, sans-serif; min-height: 44px; padding: 0.4rem 0.75rem;
  width: auto; background: transparent; color: var(--ink); border: 1px solid var(--line);
  border-radius: 10px; cursor: pointer;
}
#meshStrip input {
  width: min(100%, 16rem); padding: 0.5rem 0.6rem; border: 1px solid var(--line);
  border-radius: 10px; background: var(--field); color: var(--ink); font: inherit; min-height: 44px;
}
.mesh-actions { display: flex; flex-wrap: wrap; gap: 0.45rem; align-items: center; }
#meshProducts { flex-basis: 100%; margin: 0; overflow-wrap: anywhere; }
.cite { margin-top: 1.5rem; }
footer { margin-top: 1.75rem; color: var(--muted); font-size: 0.9rem; }
footer p { margin: 0.3rem 0; }
@media (min-width: 560px) {
  .hero-actions { flex-direction: row; align-items: center; }
  a.btn.primary { width: auto; min-width: 15.5rem; }
  button.btn.ghost { width: auto; }
  .actions { flex-direction: row; flex-wrap: wrap; }
  button.ghost { width: auto; }
}
@media (min-width: 720px) {
  .features, .grid { grid-template-columns: 1fr 1fr; }
  .wrap { padding: 2rem 1.5rem 4rem; }
}
@media (min-width: 900px) {
  .hero-grid { grid-template-columns: minmax(0, 1.15fr) minmax(16rem, 0.85fr); gap: 2.4rem; }
}
</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="wrap">
<main id="main">
  <header class="hero">
    <div class="hero-grid">
      <div>
        <div class="brandrow">
          <img class="brandmark" src="/sigil.png" width="40" height="40" alt="" decoding="async">
          <p class="stamp">Aziel Eliab</p>
        </div>
        <h1>VibeLock</h1>
        <p class="motto">${escapeHtml(MOTTO)}</p>
        <p class="lede">Physics and audio-visual deepfake risk assessment for a voice, a still, or a talking head.</p>
        <div class="hero-actions">
          <a id="download" class="btn primary dl" href="/download?asset=${DEFAULT_ASSET}" aria-describedby="os-line">Download</a>
          <button type="button" class="btn ghost" id="install-btn">One-click install</button>
        </div>
        <p class="os" id="os-line">One Python package for macOS, Linux, and Windows.</p>
        <pre id="install-cmd">${escapeHtml(INSTALL_LINE)}</pre>
        <p class="limit">Risk assessment, not a lie detector and not courtroom proof. The hosted page is not a live microphone.</p>
      </div>
      <figure class="markplate">
        <div class="stage-top">
          <img src="/sigil.png" width="28" height="28" alt="" decoding="async">
          <span>On this page</span>
        </div>
        <ol>
          <li><b>1</b><span>Paste notes, or choose a WAV or a still.</span></li>
          <li><b>2</b><span>This browser reads limited audio or image metrics.</span></li>
          <li><b>3</b><span>POST /v1/analyze returns a verdict and the checks.</span></li>
        </ol>
        <figcaption>Hosted preview. After Download, <code>vibelock ui</code> decodes on 127.0.0.1:8760.</figcaption>
      </figure>
    </div>
    <nav class="toc" aria-label="Product">
      <a href="#workspace">Preview</a>
      <a href="#features">Features</a>
      <a href="#meshStrip">Live Nodes</a>
      <a href="#counts">Downloads</a>
      <a href="#cite">Cite</a>
      <a href="${GITHUB_REPO}">GitHub</a>
    </nav>
  </header>

  <section class="block" id="features">
    <h2>What it checks</h2>
    <ul class="features">
      <li>
        <h3>Voice</h3>
        <p>Pitch, formants, phase, and decay from a WAV or from numbers you paste.</p>
      </li>
      <li>
        <h3>Still</h3>
        <p>Block edges, noise, seams, and color drift. This browser measures the image, then sends those numbers.</p>
      </li>
      <li>
        <h3>Talking head</h3>
        <p>Paste sync numbers here, or use the local app to compare the waveform with mouth motion.</p>
      </li>
      <li>
        <h3>This computer</h3>
        <p>Download, then run <code>vibelock ui</code>. Full decode stays on 127.0.0.1:8760.</p>
      </li>
    </ul>
  </section>

  <section class="block card" id="workspace">
    <h2>Preview</h2>
    <p class="help">Run VibeLock in this browser. Paste feature notes, fill the same fields as <code>POST /v1/analyze</code>, or upload a WAV or still. This browser extracts limited PCM or visual metrics. The Worker does not decode pixels on the server.</p>
    <form id="analyze-form">
      <label for="notes">Notes or JSON (features / visual / video / pitch / av)</label>
      <textarea id="notes" maxlength="8000" placeholder="rms: 0.08&#10;zcr: 0.07&#10;visual.blockiness: 1.8&#10;pitch.f0_jump: 8.5&#10;or paste a /v1/analyze JSON body"></textarea>
      <label for="media">Upload WAV or a still (browser extracts PCM or visual metrics; server does not decode pixels)</label>
      <input id="media" type="file" accept="audio/*,image/*,.wav,.png,.jpg,.jpeg,.ppm">
      <details>
        <summary>Feature fields (same keys as /v1/analyze and /v1/detect)</summary>
        <p class="help">Audio / pitch</p>
        <div class="grid">
          <div><label for="f-rms">rms</label><input id="f-rms" type="number" step="any" inputmode="decimal"></div>
          <div><label for="f-zcr">zcr</label><input id="f-zcr" type="number" step="any" inputmode="decimal"></div>
          <div><label for="f-centroid">centroid</label><input id="f-centroid" type="number" step="any" inputmode="decimal"></div>
          <div><label for="f-env-jump">env_jump</label><input id="f-env-jump" type="number" step="any" inputmode="decimal"></div>
          <div><label for="f-formant">formant_jump_hz</label><input id="f-formant" type="number" step="any" inputmode="decimal"></div>
          <div><label for="f-f0-jump">f0_jump</label><input id="f-f0-jump" type="number" step="any" inputmode="decimal"></div>
          <div><label for="f-f0-cv">f0_cv</label><input id="f-f0-cv" type="number" step="any" inputmode="decimal"></div>
          <div><label for="f-rate">rate (Hz)</label><input id="f-rate" type="number" step="1" placeholder="16000"></div>
        </div>
        <p class="help">Visual / temporal / A/V</p>
        <div class="grid">
          <div><label for="v-block">blockiness</label><input id="v-block" type="number" step="any" inputmode="decimal"></div>
          <div><label for="v-noise">noise_cv</label><input id="v-noise" type="number" step="any" inputmode="decimal"></div>
          <div><label for="v-peak">spec_peak_ratio</label><input id="v-peak" type="number" step="any" inputmode="decimal"></div>
          <div><label for="v-chroma">chroma_spread</label><input id="v-chroma" type="number" step="any" inputmode="decimal"></div>
          <div><label for="v-seam">seam_frac</label><input id="v-seam" type="number" step="any" inputmode="decimal"></div>
          <div><label for="t-flicker">flicker</label><input id="t-flicker" type="number" step="any" inputmode="decimal"></div>
          <div><label for="t-flow">flow_rough</label><input id="t-flow" type="number" step="any" inputmode="decimal"></div>
          <div><label for="t-id">identity_jump</label><input id="t-id" type="number" step="any" inputmode="decimal"></div>
          <div><label for="a-corr">av_corr</label><input id="a-corr" type="number" step="any" inputmode="decimal"></div>
          <div><label for="a-delay">delay_s</label><input id="a-delay" type="number" step="any" inputmode="decimal"></div>
        </div>
      </details>
      <div class="actions">
        <button type="submit" id="analyze-btn">Analyze</button>
        <button type="button" class="ghost" id="sample-tone">Sample tone</button>
        <button type="button" class="ghost" id="sample-photo">Sample photo</button>
        <button type="button" class="ghost" id="sample-fake">Sample deepfake</button>
      </div>
    </form>
    <p class="err" id="err" hidden role="alert"></p>
    <div class="answer" id="result" hidden aria-live="polite">
      <h2>Result</h2>
      <div class="score-wrap">
        <div class="score" id="score">—</div>
        <div class="score-pct" id="score-pct"></div>
        <span class="pill review" id="verdict">—</span>
      </div>
      <div class="mode" id="mode"></div>
      <div class="signals" id="signals"></div>
      <p class="plain" id="plain"></p>
      <div class="bar" aria-hidden="true"><span id="bar" style="width:0%"></span></div>
      <div class="codes" id="codes"></div>
      <ul class="checks" id="checks"></ul>
      <p class="help" id="notes-out"></p>
      <p class="help" id="limit-again"></p>
      <div class="actions">
        <button type="button" class="ghost" id="export">Export JSON report</button>
      </div>
    </div>
  </section>

  <div id="meshStrip" aria-label="Suite Live Nodes">
    <div class="live"><b id="meshLiveCount">0</b> Live Nodes</div>
    <div id="meshLine">Suite mesh: off (default). QNM-BUILD-1.0. QNS-CD-1.0 hub cite. Not an anonymity network.</div>
    <div class="rollup">live <b id="qnmLive">0</b> · locked <b id="qnmLocked">0</b> · isolated <b id="qnmIsolated">0</b></div>
    <div>No Node Gate · No auto-heal · Aziel Eliab only</div>
    <div class="mesh-actions">
      <input id="meshBearer" type="text" maxlength="80" placeholder="bearer (required to enable)" aria-label="mesh bearer">
      <button id="meshEnable" type="button" title="Enable suite mesh. Declared bearer required. Default off.">Enable</button>
      <button id="meshDisable" type="button" title="Disable suite mesh (always allowed)">Disable</button>
      <button id="meshJoin" type="button" title="Join as vibelock. Refused while mesh is OFF. No auto-join.">Join</button>
      <button id="meshLeave" type="button" title="Leave this node. No auto-heal.">Leave</button>
    </div>
    <div id="meshProducts">Catalog MCP mesh_* · FragGate slug=mesh · /v1/mesh/* PROXY · QNS-CD-1.0 hub cite · not AnonBroadcast · not AZMail ring · not a Node Gate · no public qnsd proxy</div>
  </div>

  <section class="block counts" id="counts">
    <h2>Counted downloads</h2>
    <p class="quiet-counts"><span><b>${v}</b> views</span><span><b>${n}</b> downloads</span><span><b>${u}</b> engine uses</span></p>
    <p class="meta">Download serves <code>${escapeHtml(DEFAULT_ASSET)}</code> from this Worker. Forks and branches that use the same link are counted. /v1 does not increment downloads. ${n} counted.</p>
    <p class="meta">GitHub: stars ${stars} · forks ${forks} · watchers ${watchers} · release assets ${rel}</p>
    <h3>Per repo / branch / fork</h3>
    <ul>${breakdown}</ul>
  </section>

  <section class="cite" id="cite">
    <h2>How to cite</h2>
    <p>Aziel Eliab. VibeLock. ${GITHUB_REPO}. ${HOST}.</p>
    <p><a href="${CATALOG}">Catalog</a> · <a href="${GITHUB_REPO}">GitHub</a> · <a href="${HOST}/download">Download</a> · <a href="/cite.json">cite.json</a> · <a href="/llms.txt">llms.txt</a></p>
  </section>
</main>
<footer>
  <p>Aziel Eliab · VibeLock · Apache-2.0 · forks welcome</p>
  <p><a href="/openapi.json">OpenAPI</a> · <a href="/mcp">MCP pointer</a> · <a href="/v1/mesh">/v1/mesh</a> · <a href="/v1/skill">Skill</a> · <a href="/ai">AI runtime</a> · <a href="${GITHUB_LATEST}">Releases</a> · <a href="/stats">JSON stats</a></p>
</footer>
</div>
<script>${CLIENT_JS}</script>
</body>

</html>`;
}
