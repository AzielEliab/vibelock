"""Localhost per-person event map for M.I.A.Lock.

Binds 127.0.0.1 by default. Pins show date × time × event × duration.
Basemap tiles require network; app assets are local (vendored Leaflet).
Historical documented events only — not live tracking.
"""

from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from mialock.models import PersonCase, casebook_index, load_casebook

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
STATIC_DIR = Path(__file__).resolve().parent / "static"
DATA_DIR = Path(__file__).resolve().parent / "data"

PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>M.I.A.Lock Map</title>
<link rel="stylesheet" href="/static/leaflet.css">
<style>
  :root {
    --bg0: #0f1a17;
    --bg1: #173028;
    --ink: #e7f2ec;
    --muted: #9bb5a8;
    --line: #2a453c;
    --accent: #c4a35a;
    --accent2: #3d9b84;
    --warn: #d4a574;
    --panel: rgba(12, 24, 20, 0.88);
    --pin: #e8c36a;
  }
  * { box-sizing: border-box; }
  html, body { height: 100%; margin: 0; color: var(--ink);
    font-family: "IBM Plex Sans", "Source Sans 3", "Helvetica Neue", sans-serif;
    background:
      radial-gradient(1200px 700px at 10% -10%, #1e3d34 0%, transparent 55%),
      radial-gradient(900px 600px at 100% 0%, #2a2418 0%, transparent 50%),
      linear-gradient(165deg, var(--bg0), var(--bg1) 55%, #101c19);
  }
  body { display: grid; grid-template-rows: auto 1fr; min-height: 100%; }
  header {
    display: flex; flex-wrap: wrap; gap: 1rem 1.5rem; align-items: end;
    justify-content: space-between; padding: 1rem 1.25rem 0.85rem;
    border-bottom: 1px solid var(--line);
    background: linear-gradient(180deg, rgba(8,16,14,0.75), transparent);
  }
  .brand { min-width: 14rem; }
  .brand .mark {
    font-family: "IBM Plex Mono", "Source Code Pro", ui-monospace, monospace; font-size: 0.72rem;
    letter-spacing: 0.18em; text-transform: uppercase; color: var(--accent);
    margin: 0 0 0.25rem;
  }
  h1 {
    font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif; font-weight: 700;
    font-size: clamp(1.45rem, 2.4vw, 1.9rem); margin: 0; letter-spacing: 0.01em;
  }
  .sub { margin: 0.35rem 0 0; color: var(--muted); font-size: 0.92rem; max-width: 38rem; }
  .controls { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: end; }
  label { display: grid; gap: 0.28rem; font-size: 0.75rem; color: var(--muted);
    letter-spacing: 0.04em; text-transform: uppercase; }
  select, button {
    font: inherit; color: var(--ink); background: #0c1714;
    border: 1px solid var(--line); border-radius: 8px; padding: 0.55rem 0.8rem;
  }
  select { min-width: 16rem; }
  button { cursor: pointer; background: linear-gradient(180deg, #3f8f7a, #2f6d5e);
    border-color: #4aa890; font-weight: 600; }
  button.ghost { background: transparent; border-color: var(--line); font-weight: 500; color: var(--muted); }
  main { display: grid; grid-template-columns: minmax(280px, 360px) 1fr; min-height: 0; }
  @media (max-width: 900px) {
    main { grid-template-columns: 1fr; grid-template-rows: 42vh 1fr; }
  }
  #map {
    min-height: 420px; border-left: 1px solid var(--line);
    background: #0a1210;
  }
  .side {
    overflow: auto; padding: 1rem 1rem 1.5rem;
    border-right: 1px solid transparent;
  }
  .warn {
    margin: 0 0 1rem; padding: 0.7rem 0.8rem; border-left: 3px solid var(--warn);
    background: rgba(212, 165, 116, 0.08); color: var(--warn); font-size: 0.88rem;
  }
  .person-head h2 {
    font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif; font-size: 1.25rem; margin: 0 0 0.35rem;
  }
  .person-head p { margin: 0 0 1rem; color: var(--muted); font-size: 0.92rem; }
  .legend { display: flex; flex-wrap: wrap; gap: 0.45rem; margin: 0 0 1rem; }
  .swatch {
    font-size: 0.72rem; padding: 0.2rem 0.45rem; border-radius: 999px;
    border: 1px solid var(--line); color: var(--muted);
  }
  .swatch i { display: inline-block; width: 0.55rem; height: 0.55rem;
    border-radius: 50%; margin-right: 0.3rem; vertical-align: middle; }
  .timeline { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.55rem; }
  .timeline li {
    display: grid; grid-template-columns: 4px 1fr; gap: 0.7rem;
    padding: 0.55rem 0.6rem; border-radius: 10px; cursor: pointer;
    background: rgba(255,255,255,0.02); border: 1px solid transparent;
    transition: border-color 160ms ease, transform 160ms ease, background 160ms ease;
  }
  .timeline li:hover, .timeline li.active {
    border-color: var(--accent2); background: rgba(61,155,132,0.1);
    transform: translateX(2px);
  }
  .timeline .rail { border-radius: 4px; background: var(--accent); }
  .timeline .when {
    font-family: "IBM Plex Mono", "Source Code Pro", ui-monospace, monospace; font-size: 0.78rem; color: var(--accent);
  }
  .timeline .title { margin: 0.15rem 0; font-weight: 600; }
  .timeline .meta { color: var(--muted); font-size: 0.82rem; }
  .pin-popup h3 { margin: 0 0 0.35rem; font-size: 1rem; }
  .pin-popup dl { margin: 0; display: grid; grid-template-columns: auto 1fr; gap: 0.2rem 0.65rem; }
  .pin-popup dt { color: #5b7268; font-size: 0.75rem; text-transform: uppercase; }
  .pin-popup dd { margin: 0; font-size: 0.88rem; }
  .leaflet-container { font: inherit; background: #0a1210; }
  .duration-halo {
    border-radius: 50%; background: rgba(196,163,90,0.18);
    border: 1px solid rgba(196,163,90,0.45);
  }
  .event-dot {
    width: 14px; height: 14px; border-radius: 50%;
    border: 2px solid #0c1714; box-shadow: 0 0 0 2px rgba(231,242,236,0.35);
  }
</style>
</head>
<body>
<header>
  <div class="brand">
    <p class="mark">M.I.A.Lock</p>
    <h1>Person event map</h1>
    <p class="sub">Custom map per subject. Each pin locks <strong>date × time × event × duration</strong> to a documented place — not live tracking.</p>
  </div>
  <div class="controls">
    <label>Subject
      <select id="person"></select>
    </label>
    <button type="button" id="fit">Fit pins</button>
    <button type="button" class="ghost" id="reload">Reload</button>
  </div>
</header>
<main>
  <aside class="side">
    <p class="warn">Historical presence only. UNKNOWN gaps stay unknown. A pin is not an identification.</p>
    <div class="person-head">
      <h2 id="personName">—</h2>
      <p id="personSummary"></p>
    </div>
    <div class="legend" id="legend"></div>
    <ol class="timeline" id="timeline"></ol>
  </aside>
  <div id="map" role="application" aria-label="Subject event map"></div>
</main>
<script src="/static/leaflet.js"></script>
<script>
const EVENT_COLORS = {
  missing_person_notice: "#c4a35a",
  missing_person_update: "#c4a35a",
  booking: "#3d9b84",
  arrest: "#2f8f9a",
  custody: "#267a6c",
  release: "#5aa88a",
  hearing: "#6b8cce",
  court_filing: "#5b7ab8",
  charge: "#5b7ab8",
  disposition: "#4a6aa0",
  incarceration: "#3a6e62",
  crime_incident: "#b8744a",
  homicide_victim: "#b04a4a",
  homicide_suspect_mention: "#8a3d3d",
  obituary: "#8b7a9e",
  death_notice: "#8b7a9e",
  funeral_notice: "#8b7a9e",
  news_crime_report: "#a0895a",
  discovery_lead: "#7a8790",
  unidentified_remains: "#9a6b6b"
};

const map = L.map("map", { zoomControl: true, attributionControl: true });
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap"
}).addTo(map);
map.setView([41.88, -87.63], 9);

let layer = L.layerGroup().addTo(map);
let pathLayer = L.layerGroup().addTo(map);
let currentFeatures = [];

function colorFor(event) {
  return EVENT_COLORS[event] || "#c4a35a";
}

function durationRadius(seconds) {
  if (!seconds || seconds <= 0) return 18;
  const hours = seconds / 3600;
  return Math.min(90, 18 + Math.sqrt(hours) * 14);
}

async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function renderLegend(events) {
  const root = document.getElementById("legend");
  root.innerHTML = "";
  [...new Set(events)].forEach(ev => {
    const el = document.createElement("span");
    el.className = "swatch";
    el.innerHTML = `<i style="background:${colorFor(ev)}"></i>${ev}`;
    root.appendChild(el);
  });
}

function popupHtml(p) {
  return `<div class="pin-popup">
    <h3>${p.label || p.event}</h3>
    <dl>
      <dt>Date</dt><dd>${p.date}</dd>
      <dt>Time</dt><dd>${p.time}</dd>
      <dt>Event</dt><dd>${p.event}</dd>
      <dt>Duration</dt><dd>${p.duration_label}</dd>
      <dt>Place</dt><dd>${p.place_name || "—"}</dd>
      <dt>Geo conf.</dt><dd>${Math.round((p.geo_confidence || 0) * 100)}%</dd>
      <dt>State</dt><dd>${p.verification_state}</dd>
    </dl>
  </div>`;
}

function focusPin(pinId) {
  const feat = currentFeatures.find(f => f.properties && f.properties.pin_id === pinId);
  if (!feat || !feat.geometry || feat.geometry.type !== "Point") return;
  const [lon, lat] = feat.geometry.coordinates;
  map.flyTo([lat, lon], Math.max(map.getZoom(), 12), { duration: 0.7 });
  document.querySelectorAll(".timeline li").forEach(li => {
    li.classList.toggle("active", li.dataset.pinId === pinId);
  });
}

function renderTimeline(features) {
  const root = document.getElementById("timeline");
  root.innerHTML = "";
  features
    .filter(f => f.geometry && f.geometry.type === "Point")
    .sort((a, b) => (a.properties.start_at || "").localeCompare(b.properties.start_at || ""))
    .forEach(f => {
      const p = f.properties;
      const li = document.createElement("li");
      li.dataset.pinId = p.pin_id;
      li.innerHTML = `
        <div class="rail" style="background:${colorFor(p.event)}"></div>
        <div>
          <div class="when">${p.date} · ${p.time}</div>
          <div class="title">${p.label || p.event}</div>
          <div class="meta">${p.event} · ${p.duration_label}${p.place_name ? " · " + p.place_name : ""}</div>
        </div>`;
      li.addEventListener("click", () => focusPin(p.pin_id));
      root.appendChild(li);
    });
}

function drawPerson(geojson) {
  layer.clearLayers();
  pathLayer.clearLayers();
  currentFeatures = geojson.features || [];
  const props = geojson.properties || {};
  document.getElementById("personName").textContent = props.display_name || props.subject_id || "—";
  document.getElementById("personSummary").textContent = props.summary || "";

  const points = [];
  const events = [];

  currentFeatures.forEach(f => {
    if (f.geometry && f.geometry.type === "LineString") {
      const latlngs = f.geometry.coordinates.map(([lon, lat]) => [lat, lon]);
      L.polyline(latlngs, {
        color: "#3d9b84",
        weight: 2,
        opacity: 0.75,
        dashArray: "6 8"
      }).bindTooltip("Documented event order — not inferred travel")
        .addTo(pathLayer);
      return;
    }
    if (!f.geometry || f.geometry.type !== "Point") return;
    const p = f.properties;
    events.push(p.event);
    const [lon, lat] = f.geometry.coordinates;
    points.push([lat, lon]);

    const halo = L.circleMarker([lat, lon], {
      radius: durationRadius(p.duration_seconds),
      className: "duration-halo",
      color: colorFor(p.event),
      weight: 1,
      fillColor: colorFor(p.event),
      fillOpacity: 0.12
    }).addTo(layer);

    const marker = L.circleMarker([lat, lon], {
      radius: 7,
      color: "#0c1714",
      weight: 2,
      fillColor: colorFor(p.event),
      fillOpacity: 1
    }).bindPopup(popupHtml(p)).addTo(layer);

    marker.on("click", () => focusPin(p.pin_id));
    halo.bindTooltip(`${p.date} ${p.time} · ${p.event} · ${p.duration_label}`);
  });

  renderLegend(events);
  renderTimeline(currentFeatures);
  if (points.length) {
    map.fitBounds(points, { padding: [36, 36], maxZoom: 12 });
  }
}

async function loadPeople() {
  const data = await fetchJSON("/api/people");
  const select = document.getElementById("person");
  select.innerHTML = "";
  data.people.forEach(p => {
    const opt = document.createElement("option");
    opt.value = p.subject_id;
    opt.textContent = `${p.display_name} (${p.pin_count} pins)`;
    select.appendChild(opt);
  });
  if (data.people.length) {
    select.value = data.people[0].subject_id;
    await loadSelected();
  }
}

async function loadSelected() {
  const id = document.getElementById("person").value;
  const geojson = await fetchJSON(`/api/people/${encodeURIComponent(id)}/geojson`);
  drawPerson(geojson);
}

document.getElementById("person").addEventListener("change", loadSelected);
document.getElementById("fit").addEventListener("click", () => {
  const pts = currentFeatures
    .filter(f => f.geometry && f.geometry.type === "Point")
    .map(f => [f.geometry.coordinates[1], f.geometry.coordinates[0]]);
  if (pts.length) map.fitBounds(pts, { padding: [36, 36], maxZoom: 12 });
});
document.getElementById("reload").addEventListener("click", loadPeople);

loadPeople().catch(err => {
  document.getElementById("personSummary").textContent = String(err);
});
</script>
</body>
</html>
"""


class MapState:
    def __init__(self, casebook_path: Path | None = None) -> None:
        self.casebook_path = casebook_path or (DATA_DIR / "sample_persons.json")
        self.cases: dict[str, PersonCase] = {}
        self.reload()

    def reload(self) -> None:
        loaded = load_casebook(self.casebook_path)
        self.cases = {c.subject_id: c for c in loaded}


def make_handler(state: MapState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def _send(self, code: int, body: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, payload: Any) -> None:
            raw = json.dumps(payload, indent=2).encode("utf-8")
            self._send(code, raw, "application/json; charset=utf-8")

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path

            if path in {"/", "/map"}:
                self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
                return

            if path.startswith("/static/"):
                rel = path[len("/static/") :]
                target = (STATIC_DIR / rel).resolve()
                if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.is_file():
                    self._send(404, b"not found", "text/plain")
                    return
                ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
                self._send(200, target.read_bytes(), ctype)
                return

            if path == "/api/people":
                self._json(200, casebook_index(state.cases.values()))
                return

            if path.startswith("/api/people/") and path.endswith("/geojson"):
                subject_id = path[len("/api/people/") : -len("/geojson")]
                case = state.cases.get(subject_id)
                if case is None:
                    self._json(404, {"error": "unknown subject"})
                    return
                self._json(200, case.to_geojson())
                return

            if path.startswith("/api/people/") and path.endswith("/pins"):
                subject_id = path[len("/api/people/") : -len("/pins")]
                case = state.cases.get(subject_id)
                if case is None:
                    self._json(404, {"error": "unknown subject"})
                    return
                self._json(200, case.to_dict())
                return

            if path == "/api/reload":
                qs = parse_qs(parsed.query)
                if "path" in qs:
                    state.casebook_path = Path(qs["path"][0])
                state.reload()
                self._json(200, casebook_index(state.cases.values()))
                return

            self._send(404, b"not found", "text/plain")

    return Handler


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, casebook: Path | None = None) -> None:
    state = MapState(casebook)
    handler = make_handler(state)
    httpd = ThreadingHTTPServer((host, port), handler)
    print(f"M.I.A.Lock map http://{host}:{port}/  (per-person date×time×event×duration pins)")
    print("Historical documented events only — not live tracking.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()
