# M.I.A.Lock

**Missing Individual Autonomous Lock**

AI-assisted missing-person discovery, identity correlation, evidence provenance,
and historical movement reconstruction.

> Search broadly. Match probabilistically. Challenge every hit. Preserve provenance. Verify before action.

**Product home:** [AzielEliab/mialock](https://github.com/AzielEliab/mialock)
(v0.1.0). Counted download:
[mialock-download-tracker](https://mialock-download-tracker.vibelock.workers.dev/).
This VibeLock folder is a pointer plus the original design notes — not the
product repo. Restricted law-enforcement systems are never scraped or simulated.

| Document | Purpose |
| --- | --- |
| [whitepaper.md](whitepaper.md) | Concept + software design (v1.1) |
| [source-catalog.md](source-catalog.md) | Lawful source classes: missing persons, homicides, arrests, courts, obituaries, and related public records |
| [map.md](map.md) | Per-person event map (date × time × event × duration pins) |
| [cold-case-archives.md](cold-case-archives.md) | Old newspapers / publishing archives + John/Jane Doe cold-case options |
| [schemas/](schemas/) | Machine-readable event types and adapter contracts |
| [examples/](examples/) | Worked candidate report and query families |

**Author:** Aziel Eliab  
**Status:** Shipped as its own product — [AzielEliab/mialock](https://github.com/AzielEliab/mialock)  
**Related engines:** DecisionGATE (escalation), TrajectoryLock (verified-event geometry), TemporalLock / ForgeReceipts (evidence integrity), GlossaFilter (export language)

## Hard boundaries

- Purpose-bound to legitimate missing-person and authorized investigative use.
- A search hit is not an identification.
- Historical documented events ≠ live location tracking.
- No credential theft, access bypass, or illicit private data.
- No automated accusation, dispatch, or public naming from an AI score alone.
