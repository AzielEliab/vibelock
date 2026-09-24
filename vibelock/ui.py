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
from vibelock.media import MediaError, decode_image_bytes, decode_video_bytes
from vibelock.report import LIMITATION, build_report, kid_plain, kid_sentence
from vibelock.synth import make_pair, sample_tone
from vibelock.synth_media import authentic_image, deepfake_av

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
<meta name="color-scheme" content="light dark">
<title>VibeLock</title>
<style>
  :root {
    color-scheme: light;
    --bg: #f6f3ec;
    --card: #fffdf8;
    --ink: #1c1915;
    --muted: #5c564c;
    --line: #e3d9c6;
    --accent: #c9a227;
    --on-accent: #1a1404;
    --ok: #0f6b3c;
    --warn: #8a4b08;
    --bad: #9b2c2c;
    --track: #efe8da;
    --shadow: 0 1px 2px rgba(28, 25, 21, 0.06);
  }
  @media (prefers-color-scheme: dark) {
    :root {
      color-scheme: dark;
      --bg: #12110e;
      --card: #1c1b17;
      --ink: #f4f0e6;
      --muted: #c8bfb0;
      --line: #3d3830;
      --accent: #c9a227;
      --on-accent: #1a1404;
      --ok: #8fd4ae;
      --warn: #e0b46a;
      --bad: #f0a0a0;
      --track: #2a2722;
      --shadow: none;
    }
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; background: var(--bg); color: var(--ink); }
  body {
    min-height: 100vh;
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.5;
  }
  main { max-width: 40rem; margin: 0 auto; padding: 1.75rem 1.25rem 3.5rem; }
  .top {
    display: flex; justify-content: space-between; align-items: baseline;
    gap: 0.75rem; flex-wrap: wrap; margin-bottom: 1.25rem;
  }
  .product { margin: 0; font-size: 1.05rem; font-weight: 650; letter-spacing: 0.01em; }
  .author { margin: 0.1rem 0 0; color: var(--muted); font-size: 0.92rem; }
  .local {
    margin: 0; color: var(--muted); font-size: 0.85rem;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  }
  .card {
    background: var(--card); border: 1px solid var(--line); border-radius: 14px;
    padding: 1.25rem 1.3rem 1.35rem; margin: 0.9rem 0;
    box-shadow: var(--shadow);
  }
  h1 { font-size: 1.85rem; font-weight: 650; letter-spacing: -0.02em; margin: 0 0 0.45rem; line-height: 1.2; }
  h2 { font-size: 1.05rem; font-weight: 650; margin: 0 0 0.65rem; }
  .lede { margin: 0 0 1.15rem; font-size: 1.05rem; max-width: 38rem; }
  p.help { color: var(--muted); font-size: 0.95rem; margin: 0.75rem 0 0; }
  label { display: block; font-size: 0.92rem; color: var(--muted); margin: 0.85rem 0 0.35rem; }
  input[type=file] {
    display: block; width: 100%; max-width: 100%; min-width: 0;
    background: var(--bg); color: var(--ink);
    border: 1px solid var(--line); padding: 0.55rem 0.65rem; border-radius: 8px;
  }
  .row { display: flex; gap: 0.6rem; flex-wrap: wrap; align-items: center; margin-top: 0.9rem; }
  button, summary {
    font-family: inherit; font-size: 1rem; cursor: pointer;
  }
  button {
    border-radius: 10px; padding: 0.55rem 0.95rem;
    border: 1px solid var(--line); background: transparent; color: var(--ink);
  }
  button.primary {
    display: inline-flex; align-items: center; justify-content: center;
    width: min(100%, 16rem); min-height: 3rem; padding: 0.7rem 1.2rem;
    background: var(--accent); color: var(--on-accent); font-weight: 700;
    border: 1px solid #a68516; font-size: 1.05rem;
  }
  button.ghost { background: transparent; color: var(--ink); }
  button:disabled { opacity: 0.55; cursor: wait; }
  details { padding: 0.15rem 0; }
  summary {
    font-weight: 650; padding: 0.15rem 0; list-style: none;
    display: flex; align-items: center; gap: 0.45rem;
  }
  summary::-webkit-details-marker { display: none; }
  summary::before { content: ""; width: 0.45rem; height: 0.45rem; border-right: 2px solid var(--muted); border-bottom: 2px solid var(--muted); transform: rotate(-45deg); }
  details[open] summary::before { transform: rotate(45deg); margin-top: -0.2rem; }
  .scoreline { margin: 0.2rem 0 0.7rem; color: var(--muted); }
  .score { color: var(--ink); font-size: 1.75rem; font-variant-numeric: tabular-nums; font-weight: 650; }
  .mode { color: var(--muted); font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.85rem; }
  .plain { font-size: 1.28rem; margin: 0.15rem 0 0.7rem; line-height: 1.35; }
  .plain.ok { color: var(--ok); }
  .plain.bad { color: var(--warn); }
  .bar { height: 8px; background: var(--track); border-radius: 99px; overflow: hidden; border: 1px solid var(--line); }
  .bar > span { display: block; height: 100%; background: var(--accent); width: 0%; }
  .codes { display: flex; flex-wrap: wrap; gap: 0.35rem; margin: 0.85rem 0; }
  .code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.75rem; padding: 0.2rem 0.45rem;
    border-radius: 4px; border: 1px solid var(--line); color: var(--warn); }
  .code.ok { color: var(--ok); }
  .checks { list-style: none; padding: 0; margin: 0.6rem 0 0; }
  .checks li { display: flex; justify-content: space-between; gap: 1rem;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.8rem; padding: 0.28rem 0;
    border-bottom: 1px solid var(--line); }
  .hash { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.75rem; color: var(--muted); word-break: break-all; }
  .err { color: var(--bad); margin: 0.6rem 0; }
  .sr-only {
    position: fixed; left: 0; top: 0; width: 1px; height: 1px; min-width: 0; max-width: 1px;
    padding: 0; margin: 0; overflow: hidden; clip-path: inset(50%); border: 0; opacity: 0;
  }
  footer { margin-top: 1.5rem; color: var(--muted); font-size: 0.85rem; }
  :focus-visible {
    outline: 2px solid #c9a227;
    outline-offset: 3px;
  }
  @media (max-width: 480px) {
    main { padding: 1.15rem 1rem 2.75rem; }
    h1 { font-size: 1.6rem; }
    button.primary, .row button, input[type=file] { width: 100%; }
    .row { flex-direction: column; align-items: stretch; }
  }
</style>
</head>
<body>
<main>
  <header class="top">
    <div>
      <p class="product">VibeLock</p>
      <p class="author">Aziel Eliab</p>
    </div>
    <p class="local">127.0.0.1</p>
  </header>

  <section class="card">
    <h1>Check a file</h1>
    <p class="lede">VibeLock checks whether a recording, a photo, or a short clip looks physically consistent with a real voice or camera.</p>
    <input id="air" class="sr-only" tabindex="-1" type="file" accept=".wav,.png,.ppm,audio/wav,image/png">
    <button class="primary" id="add" type="button">Add file</button>
    <p class="help" id="formats">WAV / PNG / PPM. The file stays on this computer.</p>
  </section>

  <section class="card" id="result" hidden>
    <h2>Result</h2>
    <p class="plain" id="plain"></p>
    <p class="scoreline">Score <span class="score" id="score">—</span></p>
    <div class="bar" aria-hidden="true"><span id="bar"></span></div>
    <p class="help" id="limit-again"></p>
  </section>
  <p class="err" id="err" role="alert" hidden></p>

  <details class="card" id="advanced">
    <summary>Advanced</summary>
    <p class="help">Simple shows one sentence and a score (consistent or inconsistent). Advanced adds hashes, checks, sample files, and export.</p>
    <label for="vib">Vibration WAV (optional)</label>
    <input id="vib" type="file" accept=".wav,audio/wav">
    <div class="row">
      <button class="ghost" id="tone" type="button">Sample tone</button>
      <button class="ghost" id="photo" type="button">Sample photo</button>
      <button class="ghost" id="fake" type="button">Sample deepfake</button>
      <button class="ghost" id="synth" type="button">Generate synthetic pair</button>
    </div>
    <p class="mode" id="mode"></p>
    <div class="codes" id="codes"></div>
    <p class="hash" id="hash"></p>
    <ul class="checks" id="checks"></ul>
    <p class="help" id="notes"></p>
    <div class="row">
      <button class="ghost" id="export" type="button">Export JSON report</button>
    </div>
  </details>

  <details class="card">
    <summary>About</summary>
    <p>Author Aziel Eliab. VibeLock __VERSION__.</p>
    <p>This is a media authenticity advisory (audio, image, and video), not courtroom proof.</p>
    <p>Reading happens on this computer. The page does not send the file anywhere, and it does not record telemetry.</p>
  </details>

  <footer>
    VibeLock __VERSION__ · Aziel Eliab
  </footer>
</main>
<script>
(function () {
  const $ = (id) => document.getElementById(id);
  let last = null;

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
    $("mode").textContent = data.verdict ? ((data.mode || "") + " · " + data.verdict) : (data.mode || "");
    $("bar").style.width = Math.round(s * 100) + "%";
    const plain = data.plain_sentence || (data.plain === "consistent"
      ? "This recording looks consistent with a real voice."
      : "This recording looks inconsistent — it might not match a real voice.");
    $("plain").textContent = plain;
    $("plain").className = "plain " + ((data.plain === "consistent") ? "ok" : "bad");
    $("limit-again").textContent = data.limitation || "This is a media authenticity advisory (audio, image, and video), not courtroom proof.";
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
      const name = document.createElement("span");
      name.textContent = ch.name + flag;
      const num = document.createElement("span");
      num.textContent = Number(ch.score).toFixed(3);
      li.appendChild(name);
      li.appendChild(num);
      ul.appendChild(li);
    });
    $("notes").textContent = (data.notes || []).join(" ");
    $("result").scrollIntoView({behavior: "smooth", block: "nearest"});
  }

  function fail(msg) {
    const text = String(msg || "Something went wrong.");
    $("err").hidden = false;
    $("err").textContent = /try/i.test(text) ? text : (text + " Try Add file again.");
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
    if (!file) { fail("Add a file first. WAV, PNG, or PPM is always ok."); return; }
    $("add").disabled = true;
    $("add").textContent = "Checking…";
    try {
      const name = String(file.name || "").toLowerCase();
      const blob = await b64(file);
      const payload = { filename: file.name };
      if (name.endsWith(".vlvd") || name.endsWith(".npy")) payload.frames_b64 = blob;
      else if (name.endsWith(".png") || name.endsWith(".ppm") || name.endsWith(".pgm") || name.endsWith(".jpg") || name.endsWith(".jpeg")) payload.image_b64 = blob;
      else payload.audio_b64 = blob;
      const vib = $("vib").files[0];
      if (vib) payload.vibration_b64 = await b64(vib);
      show(await post("/api/analyze", payload));
    } catch (e) { fail(String(e.message || e)); }
    finally {
      $("add").disabled = false;
      $("add").textContent = "Add file";
    }
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
  $("tone").onclick = async () => {
    $("tone").disabled = true;
    playBeep();
    try { show(await post("/api/tone", {})); }
    catch (e) { fail(String(e.message || e)); }
    finally { $("tone").disabled = false; }
  };
  $("photo").onclick = async () => {
    $("photo").disabled = true;
    try { show(await post("/api/photo", {})); }
    catch (e) { fail(String(e.message || e)); }
    finally { $("photo").disabled = false; }
  };
  $("fake").onclick = async () => {
    $("fake").disabled = true;
    try { show(await post("/api/deepfake", {})); }
    catch (e) { fail(String(e.message || e)); }
    finally { $("fake").disabled = false; }
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
    const accept = c.accept || ".wav,audio/wav";
    $("air").accept = accept;
    const names = (c.formats || ["wav"]).map((s) => String(s).replace(".", "").toUpperCase());
    $("formats").textContent = names.join(" / ") + " · max " + Math.round((c.max_bytes || 0) / (1024*1024)) + " MB · stays on this computer";
  }).catch(() => {});
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
        "formats": [s.lstrip(".") for s in suffixes] + ["png", "ppm", "vlvd"],
        "accept": accept_attr() + ",.png,image/png,.ppm,.vlvd",
        "engine": "deepfake",
        "signals": ["audio", "spatial", "temporal", "av_sync", "physics"],
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

    def _wants_json(self) -> bool:
        """True when the client asked for JSON ahead of HTML.

        Browsers send text/html first, so the page stays the human default.
        """
        accept = (self.headers.get("Accept") or "").lower()
        if "application/json" not in accept:
            return False
        html_at = accept.find("text/html")
        json_at = accept.find("application/json")
        if html_at < 0:
            return True
        return json_at < html_at

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            if self._wants_json():
                self._json(200, capabilities())
                return
            body = PAGE.encode("utf-8")
            self._send(200, body, "text/html; charset=utf-8")
            return
        if path == "/health":
            self._json(200, {"ok": True, "bind_host": DEFAULT_HOST, "name": "VibeLock", "version": __version__, "telemetry": False})
            return
        if path == "/api/capabilities":
            self._json(200, capabilities())
            return
        self._json(404, {"error": "not found", "hint": "Open / or GET /api/capabilities"})

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
            if path == "/api/photo":
                img = authentic_image(96, 96, seed=20260904)
                result = analyze(image=img)
                payload = build_report(result, filename="sample-photo.png", extra={"sample_photo": True})
                dlog(f"photo score={result.score:.3f} plain={kid_plain(result.score)}")
                self._json(200, payload)
                return
            if path == "/api/deepfake":
                clip = deepfake_av(duration_s=0.40, sr=16000, fps=25.0, seed=20260904)
                result = analyze(clip.audio, clip.sr, frames=clip.frames, fps=clip.fps)
                payload = build_report(result, filename="sample-deepfake.vlvd", extra={"sample_deepfake": True})
                dlog(f"deepfake score={result.score:.3f} plain={kid_plain(result.score)}")
                self._json(200, payload)
                return
            if path == "/api/analyze":
                body = self._read_json()
                filename = str(body.get("filename") or "media")
                audio = None
                sr = 0
                digest = None
                vibration = None
                vib_hash = None
                image = None
                frames = None
                fps = float(body.get("fps") or 0.0)
                if body.get("audio_b64"):
                    audio, sr, digest = _decode_field(str(body["audio_b64"]), filename)
                    if body.get("vibration_b64"):
                        vib, vsr, vib_hash = _decode_field(str(body["vibration_b64"]), str(body.get("vibration_name") or "vib.wav"))
                        if vsr != sr:
                            vib = resample(vib, vsr, sr)
                        n = min(audio.size, vib.size)
                        audio, vibration = audio[:n], vib[:n]
                if body.get("image_b64"):
                    raw = _b64_to_bytes(str(body["image_b64"]))
                    image = decode_image_bytes(raw, name=filename)
                    digest = digest or sha256_bytes(raw)
                if body.get("frames_b64"):
                    raw = _b64_to_bytes(str(body["frames_b64"]))
                    frames, file_fps = decode_video_bytes(raw, name=filename)
                    fps = fps or file_fps
                    digest = digest or sha256_bytes(raw)
                if audio is None and image is None and frames is None:
                    self._json(400, {"error": "Add a file first. Choose Add file, or open Advanced for a sample."})
                    return
                result = analyze(audio, sr or None, vibration=vibration, image=image, frames=frames, fps=fps or None)
                payload = build_report(
                    result,
                    sha256=digest,
                    sha256_vibration=vib_hash,
                    filename=filename,
                )
                dlog(f"analyze {filename} score={result.score:.3f}")
                self._json(200, payload)
                return
        except (AudioError, MediaError) as exc:
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
    sys.stdout.write(f"Open {url}\n")
    sys.stdout.flush()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        sys.stdout.write("\nstopped\n")
    finally:
        httpd.server_close()
