# Per-person event map

Each subject gets a **custom map** of documented historical pins.

Every pin locks four fields to a place:

| Field | Meaning |
| --- | --- |
| **Date** | Calendar day of the event (`start_at`) |
| **Time** | Clock time with timezone |
| **Event** | Event class (`booking`, `hearing`, `obituary`, …) |
| **Duration** | `end_at - start_at`, or explicit `duration_seconds` |

Halo size on the map scales with duration (custody windows read larger than
instant discovery leads). A dashed path follows **documented event order only**
— it is not inferred travel. UNKNOWN gaps remain unknown. This is not live
tracking.

## Run

```bash
pip install -e .
python -m mialock map
```

Open http://127.0.0.1:8765/

Use **Search mode** for:

- `archives` — old newspapers, library digital collections, publishing
- `doe_cold` — John Doe / Jane Doe / unidentified remains
- `cold_missing` — long-term missing + archives + Doe cross-match

```bash
python -m mialock people
python -m mialock search-options
python -m mialock queries doe_cold --name "Elena Vargas" --jurisdiction Illinois --age-band 20-30 --sex female
python -m mialock geojson subj-elena-cold-demo --mode doe_cold
```

See [cold-case-archives.md](cold-case-archives.md).

## Data shape

See [schemas/event_pin.schema.json](schemas/event_pin.schema.json) and the
packaged demo casebook `mialock/data/sample_persons.json`.
