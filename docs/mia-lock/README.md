# M.I.A.Lock

**Missing Individual Autonomous Lock**

AI-assisted missing-person discovery, identity correlation, evidence provenance,
and historical movement reconstruction.

> Search broadly. Match probabilistically. Challenge every hit. Preserve provenance. Verify before action.

This folder holds the concept and software design for M.I.A.Lock. It is **design documentation**, not a deployed search crawler. Restricted law-enforcement systems are never scraped or simulated.

| Document | Purpose |
| --- | --- |
| [whitepaper.md](whitepaper.md) | Concept + software design (v1.1) |
| [source-catalog.md](source-catalog.md) | Lawful source classes: missing persons, homicides, arrests, courts, obituaries, and related public records |
| [map.md](map.md) | Per-person event map (date × time × event × duration pins) |
| [schemas/](schemas/) | Machine-readable event types and adapter contracts |
| [examples/](examples/) | Worked candidate report and query families |

**Author:** Aziel Eliab  
**Status:** Design / specification  
**Related engines:** DecisionGATE (escalation), TrajectoryLock (verified-event geometry), TemporalLock / ForgeReceipts (evidence integrity), GlossaFilter (export language)

## Hard boundaries

- Purpose-bound to legitimate missing-person and authorized investigative use.
- A search hit is not an identification.
- Historical documented events ≠ live location tracking.
- No credential theft, access bypass, or illicit private data.
- No automated accusation, dispatch, or public naming from an AI score alone.
