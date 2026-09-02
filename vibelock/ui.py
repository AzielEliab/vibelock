"""Localhost UI for VibeLock. Binds 127.0.0.1. No CDN, no outbound calls."""

from __future__ import annotations

import base64
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from vibelock import __version__, analyze
from vibelock.debug import log as dlog
from vibelock.dsp import resample
from vibelock.io import (
    MAX_AUDIO_BYTES,
    AudioError,
    accept_attr,
    decode_audio_bytes,
    sha256_bytes,
    supported_suffixes,
)
from vibelock.report import LIMITATION, build_report, kid_plain, kid_sentence
from vibelock.synth import make_pair, sample_tone

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8760
LOOPBACK = frozenset({"127.0.0.1", "localhost", "::1"})
MAX_BODY = MAX_AUDIO_BYTES
TELEMETRY = False

PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VibeLock</title>
<style>
  :root {
    --bg: #0c1118;
    --card: #141c27;
    --ink: #e8eef6;
    --muted: #8fa0b5;
    --line: #243044;
    --accent: #3ec6b0;
    --accent-dim: #1b4f48;
    --warn: #e0b46a;
    --bad: #e07a7a;
    --ok: #7dcea0;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; background: var(--bg); color: var(--ink);
    font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif; }
  body { min-height: 100vh; }
  main { max-width: 42rem; margin: 0 auto; padding: 2.4rem 1.25rem 4rem; }
  header { margin-bottom: 1.4rem; }
  .mark { font-size: 0.72rem; letter-spacing: 0.22em; text-transform: uppercase;
    color: var(--accent); margin: 0 0 0.45rem; }
  h1 { font-weight: 500; letter-spacing: 0.04em; font-size: 2.1rem; margin: 0 0 0.4rem; }
  .motto { font-style: italic; color: var(--muted); margin: 0; }
  .local { display: inline-block; margin-top: 0.85rem; font-size: 0.78rem;
    letter-spacing: 0.04em; color: var(--muted); border: 1px solid var(--line);
    padding: 0.2rem 0.55rem; border-radius: 999px; font-family: ui-monospace, monospace; }
  .limit { margin: 1rem 0 0; color: var(--warn); font-size: 0.95rem; }
  .card { background: var(--card); border: 1px solid var(--line); border-radius: 12px;
    padding: 1.15rem 1.2rem 1.25rem; margin: 1.1rem 0; }
  h2 { font-size: 1.02rem; font-weight: 500; margin: 0 0 0.75rem; letter-spacing: 0.03em; }
  p.help { color: var(--muted); font-size: 0.92rem; margin: 0 0 0.9rem; }
  label { display: block; font-size: 0.82rem; color: var(--muted); margin: 0.55rem 0 0.28rem; }
  input[type=file], select { width: 100%; background: #0c1118; color: var(--ink);
    border: 1px solid var(--line); padding: 0.45rem 0.55rem; border-radius: 6px; }
  .row { display: flex; gap: 0.7rem; flex-wrap: wrap; align-items: center; margin-top: 0.9rem; }
  button { font-family: inherit; cursor: pointer; border-radius: 8px; padding: 0.55rem 1.1rem;
    border: 1px solid var(--accent); background: var(--accent-dim); color: var(--ink); }
  button.primary { background: var(--accent); color: #06221e; font-weight: 600; border: 0; }
  button.ghost { background: transparent; color: var(--muted); border-color: var(--line); }
  button:disabled { opacity: 0.5; cursor: wait; }
  .addfile { display: flex; align-items: center; justify-content: center; text-align: center;
    width: 100%; min-height: 9.5rem; font-size: 2rem; font-weight: 650; letter-spacing: 0.02em;
    border: 2px dashed var(--accent); background: var(--accent-dim); color: var(--ink);
    border-radius: 14px; cursor: pointer; margin: 0.2rem 0 0.6rem; }
  .addfile:hover { filter: brightness(1.08); }
  .views { display: inline-flex; border: 1px solid var(--line); border-radius: 999px; overflow: hidden; }
  .views button { border: 0; border-radius: 0; padding: 0.35rem 0.9rem; background: transparent; color: var(--muted); }
  .views button.on { background: var(--accent); color: #06221e; font-weight: 650; }
  .score-wrap { display: flex; align-items: baseline; gap: 0.85rem; margin: 0.4rem 0 0.5rem; }
  .score { font-size: 3rem; font-variant-numeric: tabular-nums; letter-spacing: -0.03em; }
  .mode { color: var(--muted); font-family: ui-monospace, monospace; font-size: 0.85rem; }
  .plain { font-size: 1.35rem; margin: 0.4rem 0 0.8rem; }
  .plain.ok { color: var(--ok); }
  .plain.bad { color: var(--warn); }
  .bar { height: 8px; background: #0c1118; border-radius: 99px; overflow: hidden; border: 1px solid var(--line); }
  .bar > span { display: block; height: 100%; background: var(--accent); }
  .codes { display: flex; flex-wrap: wrap; gap: 0.35rem; margin: 0.85rem 0; }
  .code { font-family: ui-monospace, monospace; font-size: 0.75rem; padding: 0.2rem 0.45rem;
    border-radius: 4px; border: 1px solid var(--line); color: var(--warn); }
  .code.ok { color: var(--ok); }
  .checks { list-style: none; padding: 0; margin: 0.6rem 0 0; }
  .checks li { display: flex; justify-content: space-between; gap: 1rem;
    font-family: ui-monospace, monospace; font-size: 0.8rem; padding: 0.28rem 0;
    border-bottom: 1px solid #1c2736; }
  .hash { font-family: ui-monospace, monospace; font-size: 0.72rem; color: var(--muted); word-break: break-all; }
  .err { color: var(--bad); }
  .sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
    overflow: hidden; clip: rect(0,0,0,0); border: 0; }
  footer { margin-top: 2rem; color: #6d7c8f; font-size: 0.8rem; }
  footer code { color: var(--muted); }
  .adv-only.hidden, .simple-only.hidden { display: none; }
</style>
</head>
<body>
<main>
  <header>
    <p class="mark">Aziel Eliab · July 2026</p>
    <h1>VibeLock</h1>
    <p class="motto">Sound can be forged. Physics is harder to fake.</p>
    <span class="local">localhost · 127.0.0.1 · never uploaded · no telemetry</span>
    <p class="limit">This is an audio authenticity advisory, not courtroom proof.</p>
  </header>

  <section class="card">
    <h2>Add a recording</h2>
    <p class="help">Tap the giant button. Your file stays on this computer. Nothing is sent to the internet.</p>
    <input id="air" class="sr-only" type="file" accept=".wav,audio/wav">
    <button class="addfile" id="add" type="button">Add file</button>
    <p class="help" id="formats">WAV files</p>
    <label class="adv-only hidden">Vibration WAV (optional)</label>
    <input id="vib" class="adv-only hidden" type="file" accept=".wav,audio/wav">
    <div class="row">
      <button class="ghost" id="tone" type="button">Sample tone</button>
      <button class="ghost adv-only hidden" id="synth" type="button">Generate synthetic pair</button>
    </div>
  </section>

  <section class="card">
    <h2>View</h2>
    <div class="views" role="group" aria-label="Simple or advanced">
      <button type="button" id="view-simple" class="on">Simple</button>
      <button type="button" id="view-advanced">Advanced</button>
    </div>
    <p class="help">Simple shows one score and consistent / inconsistent. Advanced shows hashes and checks.</p>
  </section>

  <section class="card" id="result" hidden>
    <h2>Result</h2>
    <div class="score-wrap">
      <div class="score" id="score">—</div>
      <div class="mode" id="mode"></div>
    </div>
    <p class="plain" id="plain"></p>
    <div class="bar"><span id="bar" style="width:0%"></span></div>
    <div class="adv-only hidden">
      <div class="codes" id="codes"></div>
      <p class="hash" id="hash"></p>
      <ul class="checks" id="checks"></ul>
      <p class="help" id="notes"></p>
    </div>
    <p class="help" id="limit-again"></p>
    <div class="row">
      <button class="primary" id="export" type="button">Export JSON report</button>
    </div>
  </section>
  <p class="err" id="err" hidden></p>

  <footer>
    VibeLock __VERSION__ · Apache-2.0 · forks welcome
    · <code>vibelock ui</code>
    · advisory, not courtroom proof
  </footer>

<section class="card" id="aziel-json-io">
  <h2>Import / Export JSON</h2>
  <p class="help">Tap Import JSON file to pick a .json. Export JSON saves the current session locally. Nothing is uploaded.</p>
  <input id="aziel-import-json" type="file" accept="application/json,.json">
  <p>
    <button type="button" id="aziel-import-json-btn">Import JSON file</button>
    <button type="button" id="aziel-export-json-btn">Export JSON</button>
  </p>
  <p class="help" id="aziel-json-status"></p>
</section>

</main>
<script>
(function () {
  const $ = (id) => document.getElementById(id);
  let last = null;
  let advanced = false;
  let accept = ".wav,audio/wav";

  function setView(isAdvanced) {
    advanced = isAdvanced;
    $("view-simple").classList.toggle("on", !advanced);
    $("view-advanced").classList.toggle("on", advanced);
    document.querySelectorAll(".adv-only").forEach((el) => {
      el.classList.toggle("hidden", !advanced);
    });
  }

  function b64(file) {
    return new Promise((resolve, reject) => {
      const r = new FileReader();
      r.onload = () => {
        const s = String(r.result || "");
        const i = s.indexOf(",");
        resolve(i >= 0 ? s.slice(i + 1) : s);
      };
      r.onerror = () => reject(r.error);
      r.readAsDataURL(file);
    });
  }

  function show(data) {
    last = data;
    $("err").hidden = true;
    $("result").hidden = false;
    const s = Number(data.score);
    $("score").textContent = s.toFixed(3);
    $("mode").textContent = data.mode || "";
    $("bar").style.width = Math.round(s * 100) + "%";
    const plain = data.plain_sentence || (data.plain === "consistent"
      ? "This recording looks consistent with a real voice."
      : "This recording looks inconsistent — it might not match a real voice.");
    $("plain").textContent = plain;
    $("plain").className = "plain " + ((data.plain === "consistent") ? "ok" : "bad");
    $("limit-again").textContent = data.limitation || "This is an audio authenticity advisory, not courtroom proof.";
    const codes = data.reason_codes || [];
    const box = $("codes");
    box.innerHTML = "";
    if (!codes.length) {
      const el = document.createElement("span");
      el.className = "code ok";
      el.textContent = "no reason codes";
      box.appendChild(el);
    } else {
      codes.forEach((c) => {
        const el = document.createElement("span");
        el.className = "code";
        el.textContent = c;
        box.appendChild(el);
      });
    }
    const hashes = data.hashes || {};
    const bits = [];
    if (hashes.sha256) bits.push("SHA-256 " + hashes.sha256);
    if (hashes.sha256_vibration) bits.push("vibration " + hashes.sha256_vibration);
    $("hash").textContent = bits.join(" · ");
    const ul = $("checks");
    ul.innerHTML = "";
    (data.checks || []).forEach((ch) => {
      const li = document.createElement("li");
      const flag = ch.reason_code ? "  [" + ch.reason_code + "]" : "";
      li.innerHTML = "<span>" + ch.name + flag + "</span><span>" + Number(ch.score).toFixed(3) + "</span>";
      ul.appendChild(li);
    });
    $("notes").textContent = (data.notes || []).join(" ");
  }

  function fail(msg) {
    $("err").hidden = false;
    $("err").textContent = msg;
  }

  async function post(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || ("HTTP " + res.status));
    return data;
  }

  async function runFile(file) {
    if (!file) { fail("Add a file first. WAV is always ok."); return; }
    $("add").disabled = true;
    try {
      const payload = { audio_b64: await b64(file), filename: file.name };
      const vib = $("vib").files[0];
      if (vib) payload.vibration_b64 = await b64(vib);
      show(await post("/api/analyze", payload));
    } catch (e) { fail(String(e.message || e)); }
    finally { $("add").disabled = false; }
  }

  function playBeep() {
    try {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      const ctx = new Ctx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.value = 440;
      gain.gain.value = 0.08;
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.55);
      osc.stop(ctx.currentTime + 0.6);
    } catch (e) { /* playing is optional */ }
  }

  $("add").onclick = () => $("air").click();
  $("air").onchange = () => runFile($("air").files[0]);
  $("view-simple").onclick = () => setView(false);
  $("view-advanced").onclick = () => setView(true);
  $("tone").onclick = async () => {
    $("tone").disabled = true;
    playBeep();
    try { show(await post("/api/tone", {})); }
    catch (e) { fail(String(e.message || e)); }
    finally { $("tone").disabled = false; }
  };
  $("synth").onclick = async () => {
    $("synth").disabled = true;
    try { show(await post("/api/synth", {})); }
    catch (e) { fail(String(e.message || e)); }
    finally { $("synth").disabled = false; }
  };
  $("export").onclick = () => {
    if (!last) { fail("Add a file first, then export."); return; }
    const blob = new Blob([JSON.stringify(last, null, 2)], {type: "application/json"});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "vibelock-report.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  };

  fetch("/api/capabilities").then((r) => r.json()).then((c) => {
    accept = c.accept || accept;
    $("air").accept = accept;
    const names = (c.formats || ["wav"]).map((s) => String(s).replace(".", "").toUpperCase());
    $("formats").textContent = names.join(" / ") + " · max " + Math.round((c.max_bytes || 0) / (1024*1024)) + " MB";
  }).catch(() => {});

  setView(false);
})();
</script>

<script>
(function(){
  var file = document.getElementById("aziel-import-json");
  var imp = document.getElementById("aziel-import-json-btn");
  var exp = document.getElementById("aziel-export-json-btn");
  var status = document.getElementById("aziel-json-status");
  if (!file || !imp || !exp) return;
  function say(m){ if (status) status.textContent = m; }
  function collect(){
    var data = { product: document.title || "", exported_at: new Date().toISOString(), author: "Aziel Eliab" };
    document.querySelectorAll("input, select, textarea").forEach(function(el){
      if (!el.id || el.type === "file" || el.type === "password") return;
      data[el.id] = el.type === "checkbox" ? el.checked : el.value;
    });
    if (window.__azielLastJson && typeof window.__azielLastJson === "object") {
      data.last = window.__azielLastJson;
    }
    return data;
  }
  function apply(obj){
    if (!obj || typeof obj !== "object") return;
    window.__azielLastJson = obj;
    Object.keys(obj).forEach(function(k){
      if (k === "last" || k === "product" || k === "exported_at" || k === "author") return;
      var el = document.getElementById(k);
      if (!el || el.type === "file" || el.type === "password") return;
      if (el.type === "checkbox") el.checked = !!obj[k];
      else if ("value" in el) el.value = obj[k];
    });
    var ta = document.querySelector("textarea");
    if (ta && obj && !obj[ta.id] && typeof obj === "object") {
      try { if (!ta.value) ta.value = JSON.stringify(obj, null, 2); } catch (e) {}
    }
  }
  imp.addEventListener("click", function(){ file.click(); });
  file.addEventListener("change", function(){
    var f = file.files && file.files[0];
    if (!f) return;
    var r = new FileReader();
    r.onload = function(){
      try { apply(JSON.parse(String(r.result || "{}"))); say("Imported " + f.name); }
      catch (e) { say("Invalid JSON"); }
    };
    r.readAsText(f);
  });
  exp.addEventListener("click", function(){
    var blob = new Blob([JSON.stringify(collect(), null, 2)], {type: "application/json"});
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "session.json";
    a.click();
    setTimeout(function(){ URL.revokeObjectURL(a.href); }, 800);
    say("Exported JSON");
  });
})();
</script>

</body>
</html>
""".replace("__VERSION__", __version__)


def capabilities() -> dict[str, Any]:
    suffixes = list(supported_suffixes())
    return {
        "ok": True,
        "product": "vibelock",
        "version": __version__,
        "formats": [s.lstrip(".") for s in suffixes],
        "accept": accept_attr(),
        "max_bytes": MAX_BODY,
        "limitation": LIMITATION,
        "loopback": True,
        "telemetry": TELEMETRY,
        "courtroom_proof": False,
        "views": ["simple", "advanced"],
    }


def _b64_to_bytes(blob: str) -> bytes:
    raw = base64.b64decode(blob)
    if len(raw) > MAX_BODY:
        raise AudioError("That file is too big. Please use a smaller recording.")
    return raw


def _decode_field(blob: str, filename: str = "") -> tuple[Any, int, str]:
    raw = _b64_to_bytes(blob)
    audio, sr = decode_audio_bytes(raw, name=filename)
    return audio, sr, sha256_bytes(raw)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj: Any) -> None:
        raw = json.dumps(obj, indent=2).encode("utf-8")
        self._send(code, raw, "application/json; charset=utf-8")

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise AudioError("That file is too big. Please use a smaller recording.")
        raw = self.rfile.read(length) if length else b"{}"
        data = json.loads(raw.decode("utf-8") or "{}")
        if not isinstance(data, dict):
            raise ValueError("expected a JSON object")
        return data

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            body = PAGE.encode("utf-8")
            self._send(200, body, "text/html; charset=utf-8")
            return
        if path == "/health":
            self._json(200, {"ok": True, "bind_host": DEFAULT_HOST, "name": "VibeLock", "version": __version__, "telemetry": False})
            return
        if path == "/api/capabilities":
            self._json(200, capabilities())
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            if path == "/api/synth":
                pair = make_pair(duration_s=1.0, sr=16000, f0=120.0, seed=20260728)
                result = analyze(pair.audio, pair.sr, vibration=pair.vibration)
                payload = build_report(result, filename="synthetic-pair.wav", extra={"synthetic": True})
                dlog(f"synth score={result.score:.3f} plain={kid_plain(result.score)}")
                self._json(200, payload)
                return
            if path == "/api/tone":
                tone = sample_tone(duration_s=0.8, sr=16000, freq=440.0)
                result = analyze(tone, 16000)
                payload = build_report(result, filename="sample-tone.wav", extra={"sample_tone": True})
                dlog(f"tone score={result.score:.3f} plain={kid_plain(result.score)}")
                self._json(200, payload)
                return
            if path == "/api/analyze":
                body = self._read_json()
                audio_b64 = body.get("audio_b64")
                if not audio_b64:
                    self._json(400, {"error": "Add a file first."})
                    return
                filename = str(body.get("filename") or "audio.wav")
                audio, sr, digest = _decode_field(str(audio_b64), filename)
                vibration = None
                vib_hash = None
                if body.get("vibration_b64"):
                    vib, vsr, vib_hash = _decode_field(str(body["vibration_b64"]), str(body.get("vibration_name") or "vib.wav"))
                    if vsr != sr:
                        vib = resample(vib, vsr, sr)
                    n = min(audio.size, vib.size)
                    audio, vibration = audio[:n], vib[:n]
                result = analyze(audio, sr, vibration=vibration)
                payload = build_report(
                    result,
                    sha256=digest,
                    sha256_vibration=vib_hash,
                    filename=filename,
                )
                dlog(f"analyze {filename} score={result.score:.3f} sha256={digest[:12]}")
                self._json(200, payload)
                return
        except AudioError as exc:
            self._json(400, {"error": str(exc), "limitation": LIMITATION})
            return
        except Exception as exc:  # noqa: BLE001 — never crash the UI process
            dlog(f"ui error: {exc!r}")
            self._json(400, {"error": str(exc), "limitation": LIMITATION})
            return
        self._json(404, {"error": "not found"})


def make_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    if host not in LOOPBACK:
        raise ValueError("VibeLock UI binds loopback only (127.0.0.1)")
    return ThreadingHTTPServer((host, port), Handler)


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    httpd = make_server(host, port)
    url = f"http://{host}:{port}/"
    sys.stdout.write(f"VibeLock UI  {url}\n")
    sys.stdout.write("Local only. Audio is not retained and never leaves this process.\n")
    sys.stdout.write(LIMITATION + "\n")
    sys.stdout.flush()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        sys.stdout.write("\nstopped\n")
    finally:
        httpd.server_close()
