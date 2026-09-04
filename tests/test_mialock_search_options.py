"""Tests for archive / Doe / cold-case search options."""

from __future__ import annotations

import json

from mialock.models import load_casebook
from mialock.search_options import (
    filter_pins_by_mode,
    list_search_modes,
    render_queries,
)


def test_search_modes_include_archives_and_doe():
    modes = {m["mode_id"]: m for m in list_search_modes()}
    assert "archives" in modes
    assert modes["archives"]["archive"] is True
    assert "doe_cold" in modes
    assert modes["doe_cold"]["doe_match"] is True
    assert "cold_missing" in modes


def test_doe_queries_mention_john_and_jane():
    payload = render_queries(
        "doe_cold",
        name="Elena Vargas",
        jurisdiction="Illinois",
        age_band="20-30",
        sex="female",
    )
    text = " ".join(q["rendered"] for q in payload["queries"])
    assert "Jane Doe" in text
    assert "John Doe" in text
    assert payload["doe_match"] is True


def test_archive_queries_mention_newspapers():
    payload = render_queries(
        "archives",
        name="Christina Green",
        jurisdiction="Illinois",
        year_from="1990",
        year_to="1999",
    )
    text = " ".join(q["rendered"] for q in payload["queries"]).lower()
    assert "newspaper" in text or "archive" in text


def test_cold_case_demo_person_has_doe_and_archive_pins():
    cases = {c.subject_id: c for c in load_casebook()}
    cold = cases["subj-elena-cold-demo"]
    classes = {p.event_class for p in cold.pins}
    assert "jane_doe_notice" in classes
    assert "john_doe_notice" in classes
    assert "newspaper_archive_hit" in classes
    doe_pins = filter_pins_by_mode(cold.pins, "doe_cold")
    assert any(p.event_class == "jane_doe_notice" for p in doe_pins)
    archive_pins = filter_pins_by_mode(cold.pins, "archives")
    assert any(p.event_class == "newspaper_archive_hit" for p in archive_pins)


def test_geojson_mode_filters_doe(tmp_path=None):
    cold = next(c for c in load_casebook() if c.subject_id == "subj-elena-cold-demo")
    geo = cold.to_geojson("doe_cold")
    events = [
        f["properties"]["event"]
        for f in geo["features"]
        if f["geometry"]["type"] == "Point"
    ]
    assert "jane_doe_notice" in events
    assert "booking" not in events


def test_api_search_options_and_queries():
    from http.client import HTTPConnection
    from http.server import ThreadingHTTPServer
    import threading

    from mialock.map_ui import MapState, make_handler

    state = MapState()
    handler = make_handler(state)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        conn = HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/api/search-options")
        res = conn.getresponse()
        body = json.loads(res.read().decode())
        assert res.status == 200
        ids = {m["mode_id"] for m in body["modes"]}
        assert {"archives", "doe_cold", "cold_missing"} <= ids

        conn.request(
            "GET",
            "/api/people/subj-elena-cold-demo/queries?mode=doe_cold",
        )
        res2 = conn.getresponse()
        q = json.loads(res2.read().decode())
        assert res2.status == 200
        assert q["doe_match"] is True
        assert q["queries"]

        conn.request(
            "GET",
            "/api/people/subj-elena-cold-demo/geojson?mode=archives",
        )
        res3 = conn.getresponse()
        geo = json.loads(res3.read().decode())
        assert res3.status == 200
        assert geo["properties"]["search_mode"] == "archives"
        conn.close()
    finally:
        httpd.shutdown()
