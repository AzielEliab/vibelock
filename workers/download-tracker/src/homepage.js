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
<script type="application/ld+json">${ld}</script>
<style>
:root{--bg:#12100c;--paper:#1b1712;--ink:#efe6d6;--muted:#a89880;--line:#3a3228;--gold:#c9a227;--yes:#7dcea0;--no:#e07a7a;--rev:#e0b15a;--card:#19150f}
*{box-sizing:border-box}
html,body{background:var(--bg);color:var(--ink);margin:0}
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;line-height:1.5}
.wrap{max-width:720px;margin:auto;padding:24px 18px 80px}
.brandrow{display:flex;flex-wrap:wrap;align-items:center;gap:12px;margin:0 0 10px}
.brandmark{width:40px;height:40px;border-radius:10px;object-fit:cover;flex:0 0 auto;box-shadow:0 0 0 1px #d4af3733}
.brand{font-size:26px;font-weight:800;letter-spacing:-.02em}
.pill{border-radius:999px;padding:6px 12px;font-size:12px;font-weight:700;background:#2a241c;color:var(--ink);border:1px solid var(--line)}
.pill.yes{background:#14261c;color:var(--yes);border-color:#2e6b45}
.pill.no{background:#2a1414;color:var(--no);border-color:#8a2b2b}
.pill.review{background:#2a2210;color:var(--rev);border-color:#8a5a2b}
.pill.interesting{background:#2a2410;color:var(--gold);border-color:var(--gold)}
.author{color:var(--muted);margin:0 0 8px;font-size:14px}
.motto{color:var(--muted);font-style:italic;margin:0 0 14px}
.banner{background:#1a140c;border:1px solid #8a5a2b;border-radius:12px;padding:12px 14px;margin:0 0 16px;color:#f0d0a8;font-size:15px}
.nav2{margin:0 0 14px;font-size:14px}
.nav2 .sep{color:var(--muted);margin:0 8px}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:0 0 16px}
.stat{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:12px}
.stat b{display:block;font-size:22px;font-weight:800;font-variant-numeric:tabular-nums}
.stat span{color:var(--muted);font-size:12px}
.card,.answer{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;margin:14px 0}
h1{font-size:1.75rem;margin:0}
h2{font-size:1.15rem;margin:0 0 .7rem}
p.help{color:var(--muted);font-size:.92rem;margin:0 0 .9rem}
label{display:block;font-size:.78rem;color:var(--muted);margin:.45rem 0 .22rem}
textarea,input[type=number],input[type=file],input[type=text]{width:100%;background:#16130f;color:var(--ink);border:1px solid var(--line);border-radius:10px;padding:10px 12px;font:inherit}
textarea{min-height:110px;resize:vertical}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px 12px}
details{margin:10px 0}
details summary{cursor:pointer;color:var(--gold);font-weight:650}
button,.button{background:var(--gold);color:#14110a;border:0;padding:12px 18px;border-radius:12px;font:inherit;font-size:16px;font-weight:750;cursor:pointer;min-height:44px;display:inline-flex;align-items:center;justify-content:center;text-decoration:none}
button.ghost,.button.ghost{background:transparent;color:var(--ink);border:1px solid var(--line)}
button.copied{background:#7dcf9a;color:#0e1014}
button:disabled{opacity:.55;cursor:wait}
.actions{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0 0}
.score-wrap{display:flex;flex-wrap:wrap;align-items:baseline;gap:14px;margin:.3rem 0 .6rem}
.score{font-size:2.6rem;font-weight:800;letter-spacing:-.03em;font-variant-numeric:tabular-nums}
.score-pct{font-size:1.4rem;color:var(--gold);font-weight:750}
.mode,.signals{color:var(--muted);font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.85rem}
.plain{font-size:1.2rem;margin:.35rem 0 .7rem}
.plain.ok{color:var(--yes)}
.plain.bad{color:var(--rev)}
.bar{height:8px;background:#16130f;border-radius:99px;overflow:hidden;border:1px solid var(--line)}
.bar>span{display:block;height:100%;background:var(--gold)}
.codes{display:flex;flex-wrap:wrap;gap:.35rem;margin:.85rem 0}
.code{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.75rem;padding:.2rem .45rem;border-radius:4px;border:1px solid var(--line);color:var(--rev)}
.code.ok{color:var(--yes)}
.checks{list-style:none;padding:0;margin:.6rem 0 0}
.checks li{display:flex;justify-content:space-between;gap:1rem;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.8rem;padding:.28rem 0;border-bottom:1px solid var(--line)}
.err{color:var(--no);margin:.6rem 0 0}
.btns{display:grid;grid-template-columns:1fr 1fr;gap:.75rem;margin:.4rem 0 .85rem}
a.btn,button.btn{display:block;width:100%;box-sizing:border-box;text-align:center;font:inherit;font-size:1.15rem;font-weight:750;padding:1rem 1.1rem;border-radius:10px;border:0;cursor:pointer;text-decoration:none}
a.btn.primary{background:#efe6d6;color:#12100c}
button.btn.install{background:var(--gold);color:#14110a}
.meta{margin-top:1.1rem;color:var(--muted);font-size:.92rem}
.meta a,a{color:var(--gold)}
.iso{margin-top:.85rem;font-size:.85rem;color:#8a7a62}
pre{background:#16130f;padding:.75rem .9rem;overflow:auto;border-radius:8px;font-size:.82rem;border:1px solid var(--line)}
.cite{margin-top:1.4rem;padding-top:1rem;border-top:1px solid var(--line)}
footer{margin-top:36px;color:var(--muted);font-size:14px}
@media (max-width:720px){
  .wrap{padding:16px 14px 72px}
  .stats,.grid,.btns{grid-template-columns:1fr}
  .brand{width:100%}
  button,.button{width:100%}
  .actions{flex-direction:column}
}
</style>
</head>
<body>
<div class="wrap">
  <div class="brandrow">
    <img class="brandmark" src="/sigil.png" width="40" height="40" alt="VibeLock everblooming sigil" decoding="async">
    <div class="brand">VibeLock</div>
    <span class="pill interesting">Risk engine</span>
  </div>
  <p class="author">Author Aziel Eliab</p>
  <nav class="nav2" aria-label="Product">
    <a href="#workspace">Analyze</a><span class="sep">|</span>
    <a href="#download">Download</a><span class="sep">|</span>
    <a href="#cite">Cite</a><span class="sep">|</span>
    <a href="${GITHUB_REPO}">GitHub</a>
  </nav>
  <p class="motto">${escapeHtml(MOTTO)}</p>
  <p class="banner">${escapeHtml(BANNER)}</p>

  <div class="stats">
    <div class="stat"><b>${v}</b><span>Views</span></div>
    <div class="stat"><b>${n}</b><span>Downloads</span></div>
    <div class="stat"><b>${u}</b><span>Engine uses</span></div>
  </div>

  <section class="card" id="workspace">
    <h2>Analyze</h2>
    <p class="help">Run VibeLock in this browser. Paste feature notes, fill the same fields as <code>POST /v1/analyze</code>, or upload a WAV / still. Results are a score, verdict, and per-check metrics — software output, not a raw dump. Hosted is not a live mic.</p>
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
    <p class="err" id="err" hidden></p>
    <div class="answer" id="result" hidden>
      <h2>Result</h2>
      <div class="score-wrap">
        <div class="score" id="score">—</div>
        <div class="score-pct" id="score-pct"></div>
        <span class="pill review" id="verdict">—</span>
      </div>
      <div class="mode" id="mode"></div>
      <div class="signals" id="signals"></div>
      <p class="plain" id="plain"></p>
      <div class="bar"><span id="bar" style="width:0%"></span></div>
      <div class="codes" id="codes"></div>
      <ul class="checks" id="checks"></ul>
      <p class="help" id="notes-out"></p>
      <p class="help" id="limit-again"></p>
      <div class="actions">
        <button type="button" class="ghost" id="export">Export JSON report</button>
      </div>
    </div>
  </section>

  <section class="card" id="download">
    <h2>Download</h2>
    <p class="help"><strong>Two big buttons.</strong> Download saves the gzip (the Downloads number goes up). One-click install copies a Terminal command. After it finishes, type <code>vibelock ui</code>.</p>
    <div class="btns">
      <a class="btn primary dl" href="/download?asset=${DEFAULT_ASSET}">Download</a>
      <button type="button" class="btn install" id="install-btn">One-click install</button>
    </div>
    <pre id="install-cmd">${escapeHtml(INSTALL_LINE)}</pre>
    <p class="help">Then run: <code>vibelock ui</code> and open http://127.0.0.1:8760 (this computer only).</p>
    <p class="meta">The download count ticks on the Download click. The Worker serves the gzip (HTTP 200). No 302 to GitHub. Forks using this same link are counted automatically. ${escapeHtml(DEFAULT_ASSET)} — ${n} counted.</p>
    <p class="iso">Isolated counter: Worker <code>vibelock-download-tracker</code>, project <code>vibelock</code>, KV <code>VIBELOCK_DOWNLOADS</code>. Not mixed with any other product. /v1 does not increment downloads.</p>
    <p class="meta">GitHub: stars ${stars} · forks ${forks} · watchers ${watchers} · release assets ${rel}</p>
    <p class="meta">Apache-2.0 · Eliab, Aziel · forks welcome</p>
    <p class="meta"><a href="/stats">JSON stats</a> · <a href="/openapi.json">OpenAPI</a> · <a href="/v1/skill">Skill</a> · <a href="/ai">AI runtime</a> · <a href="${GITHUB_REPO}">GitHub</a> · <a href="${GITHUB_LATEST}">releases</a></p>
    <h2>Per repo / branch / fork</h2>
    <ul>${breakdown}</ul>
  </section>

  <section class="cite" id="cite">
    <h2>How to cite</h2>
    <p>Aziel Eliab. VibeLock. ${GITHUB_REPO}. ${HOST}.</p>
    <p><a href="${CATALOG}">Catalog</a> · <a href="${GITHUB_REPO}">GitHub</a> · <a href="${HOST}/download">Download</a> · <a href="/cite.json">cite.json</a> · <a href="/llms.txt">llms.txt</a></p>
  </section>
  <footer>Aziel Eliab · VibeLock is a product name · Apache-2.0 · forks welcome · not a lie detector · not courtroom proof</footer>
</div>
<script>${CLIENT_JS}</script>
</body>
</html>`;
}
