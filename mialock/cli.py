"""CLI for M.I.A.Lock map and casebook tools."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mialock import __version__
from mialock.map_ui import DEFAULT_HOST, DEFAULT_PORT, serve
from mialock.models import casebook_index, load_casebook


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mialock",
        description="M.I.A.Lock — per-person historical event map (date × time × event × duration).",
    )
    parser.add_argument("--version", action="version", version=f"mialock {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    map_p = sub.add_parser("map", help="Open localhost map UI for each person's pins")
    map_p.add_argument("--host", default=DEFAULT_HOST)
    map_p.add_argument("--port", type=int, default=DEFAULT_PORT)
    map_p.add_argument(
        "--casebook",
        type=Path,
        default=None,
        help="JSON casebook path (default: packaged sample_persons.json)",
    )

    list_p = sub.add_parser("people", help="List subjects in a casebook")
    list_p.add_argument("--casebook", type=Path, default=None)

    geo_p = sub.add_parser("geojson", help="Export one subject's GeoJSON")
    geo_p.add_argument("subject_id")
    geo_p.add_argument("--casebook", type=Path, default=None)
    geo_p.add_argument("-o", "--output", type=Path, default=None)

    args = parser.parse_args(argv)

    if args.cmd == "map":
        serve(host=args.host, port=args.port, casebook=args.casebook)
        return 0

    cases = load_casebook(args.casebook)
    if args.cmd == "people":
        print(json.dumps(casebook_index(cases), indent=2))
        return 0

    if args.cmd == "geojson":
        match = next((c for c in cases if c.subject_id == args.subject_id), None)
        if match is None:
            print(f"unknown subject: {args.subject_id}", file=sys.stderr)
            return 1
        payload = json.dumps(match.to_geojson(), indent=2)
        if args.output:
            args.output.write_text(payload + "\n", encoding="utf-8")
        else:
            print(payload)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
