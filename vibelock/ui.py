"""Localhost UI for VibeLock. Binds 127.0.0.1. No CDN, no outbound calls."""

from __future__ import annotations

import base64
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from typing import Any
from urllib.parse import urlparse

import numpy as np
from scipy.io import wavfile

from vibelock import __version__, analyze
from vibelock.dsp import as_mono_float, resample
from vibelock.synth import make_pair

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8760
MAX_BODY = 12 * 1024 * 1024

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
  header { margin-bottom: 1.6rem; }
  .mark { font-size: 0.72rem; letter-spacing: 0.22em; text-transform: uppercase;
    color: var(--accent); margin: 0 0 0.45rem; }
  h1 { font-weight: 500; letter-spacing: 0.04em; font-size: 2.1rem; margin: 0 0 0.4rem; }
  .motto { font-style: italic; color: var(--muted); margin: 0; }
  .local { display: inline-block; margin-top: 0.85rem; font-size: 0.78rem;
    letter-spacing: 0.04em; color: var(--muted); border: 1px solid var(--line);
    padding: 0.2rem 0.55rem; border-radius: 999px; font-family: ui-monospace, monospace; }
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
  .score-wrap { display: flex; align-items: baseline; gap: 0.85rem; margin: 0.4rem 0 0.8rem; }
  .score { font-size: 3rem; font-variant-numeric: tabular-nums; letter-spacing: -0.03em; }
  .mode { color: var(--muted); font-family: ui-monospace, monospace; font-size: 0.85rem; }
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
  .err { color: var(--bad); }
  footer { margin-top: 2rem; color: #6d7c8f; font-size: 0.8rem; }
  footer code { color: var(--muted); }
</style>
</head>
<body>
<main>
  <header>
    <p class="mark">Aziel Eliab · July 2026</p>
    <h1>VibeLock</h1>
    <p class="motto">Sound can be forged. Physics is harder to fake.</p>
    <span class="local">localhost · 127.0.0.1 · never uploaded</span>
  </header>

  <section class="card">
    <h2>Evaluate authenticity</h2>
    <p class="help">Air WAV, optional body-coupled vibration, or a synthetic physically-plausible pair generated here. DSP stays on this machine.</p>
    <label>Air microphone WAV</label>
    <input id="air" type="file" accept=".wav,audio/wav">
    <label>Vibration WAV (optional)</label>
    <input id="vib" type="file" accept=".wav,audio/wav">
    <div class="row">
      <button class="primary" id="go" type="button">Evaluate authenticity</button>
      <button class="ghost" id="synth" type="button">Generate synthetic pair</button>
    </div>
  </section>

  <section class="card" id="result" hidden>
    <h2>Result</h2>
    <div class="score-wrap">
      <div class="score" id="score">—</div>
      <div class="mode" id="mode"></div>
    </div>
    <div class="bar"><span id="bar" style="width:0%"></span></div>
    <div class="codes" id="codes"></div>
    <ul class="checks" id="checks"></ul>
    <p class="help" id="notes"></p>
  </section>
  <p class="err" id="err" hidden></p>

  <footer>
    VibeLock __VERSION__ · Apache-2.0 · forks welcome
    · <code>vibelock ui</code>
  </footer>
</main>
<script>
(function () {
  const $ = (id) => document.getElementById(id);
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
    $("err").hidden = true;
    $("result").hidden = false;
    const s = Number(data.score);
    $("score").textContent = s.toFixed(3);
    $("mode").textContent = data.mode || "";
    $("bar").style.width = Math.round(s * 100) + "%";
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
  $("go").onclick = async () => {
    const air = $("air").files[0];
    if (!air) { fail("Choose an air-microphone WAV, or generate a synthetic pair."); return; }
    $("go").disabled = true;
    try {
      const payload = { audio_b64: await b64(air), filename: air.name };
      const vib = $("vib").files[0];
      if (vib) payload.vibration_b64 = await b64(vib);
      show(await post("/api/analyze", payload));
    } catch (e) { fail(String(e.message || e)); }
    finally { $("go").disabled = false; }
  };
  $("synth").onclick = async () => {
    $("synth").disabled = true;
    try { show(await post("/api/synth", {})); }
    catch (e) { fail(String(e.message || e)); }
    finally { $("synth").disabled = false; }
  };
})();
</script>
</body>
</html>
""".replace("__VERSION__", __version__)


def _pcm_to_float(data: np.ndarray) -> np.ndarray:
    data = np.asarray(data)
    if np.issubdtype(data.dtype, np.floating):
        arr = data.astype(np.float64)
        peak = np.max(np.abs(arr)) if arr.size else 1.0
        if peak > 8.0:
            arr = arr / max(peak, 1.0)
        return as_mono_float(arr)
    info = np.iinfo(data.dtype)
    scale = float(max(abs(info.min), info.max))
    return as_mono_float(data.astype(np.float64) / scale)


def _wav_from_b64(blob: str) -> tuple[np.ndarray, int]:
    raw = base64.b64decode(blob)
    sr, data = wavfile.read(BytesIO(raw))
    return _pcm_to_float(data), int(sr)


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
            raise ValueError("payload too large")
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
            self._json(200, {"ok": True, "bind_host": DEFAULT_HOST, "name": "VibeLock"})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            if path == "/api/synth":
                pair = make_pair(duration_s=1.0, sr=16000, f0=120.0, seed=20260728)
                result = analyze(pair.audio, pair.sr, vibration=pair.vibration)
                payload = result.to_dict()
                payload["synthetic"] = True
                self._json(200, payload)
                return
            if path == "/api/analyze":
                body = self._read_json()
                audio_b64 = body.get("audio_b64")
                if not audio_b64:
                    self._json(400, {"error": "audio_b64 is required"})
                    return
                audio, sr = _wav_from_b64(str(audio_b64))
                vibration = None
                if body.get("vibration_b64"):
                    vib, vsr = _wav_from_b64(str(body["vibration_b64"]))
                    if vsr != sr:
                        vib = resample(vib, vsr, sr)
                    n = min(audio.size, vib.size)
                    audio, vibration = audio[:n], vib[:n]
                result = analyze(audio, sr, vibration=vibration)
                self._json(200, result.to_dict())
                return
        except Exception as exc:  # noqa: BLE001 — surface decode/analyze errors to the UI
            self._json(400, {"error": str(exc)})
            return
        self._json(404, {"error": "not found"})


def make_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Handler)


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    httpd = make_server(host, port)
    url = f"http://{host}:{port}/"
    sys.stdout.write(f"VibeLock UI  {url}\n")
    sys.stdout.write("Local only. Audio is not retained and never leaves this process.\n")
    sys.stdout.flush()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        sys.stdout.write("\nstopped\n")
    finally:
        httpd.server_close()
