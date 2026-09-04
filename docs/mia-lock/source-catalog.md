# M.I.A.Lock Source Catalog

Lawful public and authorized source classes the system is designed to **track,
normalize, and score** for missing-person discovery.

This is a **coverage checklist for adapters**, not a scrape-everything mandate.
Restricted law-enforcement databases are in scope only when the operator has
lawful authorization and a dedicated authorized adapter — never via scraping or
credential bypass.

Machine-readable companion: [schemas/event_types.json](schemas/event_types.json)
and [schemas/source_adapter.schema.json](schemas/source_adapter.schema.json).

---

## 1. How adapters declare coverage

Every adapter must declare:

| Field | Meaning |
| --- | --- |
| `tier` | `authoritative_public` \| `authorized_institutional` \| `independent_reporting` \| `death_remembrance` \| `discovery` |
| `event_classes[]` | Which event types this adapter can emit |
| `jurisdictions[]` | States/counties/agencies covered |
| `confirmation_capable` | Whether hits may support verification (not just leads) |
| `access_basis` | `public` \| `authorized` \| `attested` |
| `rate_limit_policy` | Robots / ToS / API limits |
| `coverage_notes` | Known gaps (e.g. “county jail only; no municipal lockup”) |

A case’s **coverage map** is the union of adapter coverage actually exercised
during search jobs, plus dead-end certificates for zero-hit runs.

---

## 2. Event classes (must be representable)

These classes are required in the normalizer even if a given deployment has not
yet implemented every adapter.

### 2.1 Missing-person and unidentified

| Code | Description | Typical sources |
| --- | --- | --- |
| `missing_person_notice` | Active or historical missing-person report / poster | Government missing portals, sheriff public missing pages, nonprofit registries with public listings, NamUs public where available |
| `missing_person_update` | Status change on an existing notice | Same as above |
| `cold_case_missing` | Long-term / cold missing listing | Cold-case public pages, long-horizon registries |
| `unidentified_remains` | Unidentified deceased / Doe notices | Medical examiner public Doe pages, NamUs Unidentified, state clearinghouses |
| `john_doe_notice` | Public unidentified **male** Doe notice | ME / NamUs / agency Doe pages |
| `jane_doe_notice` | Public unidentified **female** Doe notice | ME / NamUs / agency Doe pages |
| `cold_case_unidentified` | Explicit cold-case unidentified listing | Cold-case units’ public pages, clearinghouses |
| `found_person_notice` | Public “located / recovered” notices | Agency public releases |

Doe notices are **compatibility leads only** — never auto-merged to a named subject.

### 2.2 Arrest, booking, custody

| Code | Description | Typical sources |
| --- | --- | --- |
| `arrest` | Arrest event as published | Police blotters, agency releases, jail intake mirrors |
| `booking` | Jail booking / intake record | County sheriff inmate search, regional jail portals |
| `custody` | Currently in custody (public roster) | Inmate locators |
| `release` | Release / bond / transfer out | Jail portals, court minutes |
| `incarceration` | Prison / DOC custody | State DOC inmate search (public fields only) |
| `warrant_public` | Publicly posted warrant notice | Agency warrant lists **where lawfully published** |

### 2.3 Courts and charges

| Code | Description | Typical sources |
| --- | --- | --- |
| `charge` | Charging document / accusation summary | Court portals, clerk indexes |
| `court_filing` | Case filing / initiation | Odyssey / public access terminals / clerk sites |
| `hearing` | Scheduled or held hearing | Court calendars / dockets |
| `disposition` | Judgment, plea, dismissal, sentence | Court dockets |
| `appeal` | Appellate docket activity | State/federal public PACER-equivalent where authorized |

### 2.4 Crime incidents and homicide

| Code | Description | Typical sources |
| --- | --- | --- |
| `crime_incident` | Public blotter / incident summary | Police logs, open-data crime feeds |
| `homicide_victim` | Public identification or Doe→named victim release | Agency releases, ME offices, reputable news |
| `homicide_suspect_mention` | Public suspect/person-of-interest mention | Agency releases, charging docs, news (**role-tagged**) |
| `crime_victim_mention` | Non-homicide victim named in public source | Releases, news |
| `crime_witness_mention` | Witness named publicly (rare; handle carefully) | Releases, news |
| `public_tip_or_release` | Official LE PIO / press release | Agency newsrooms |

**Subject role is mandatory** on crime/homicide records:
`missing | victim | suspect_mention | witness_mention | unspecified`.

### 2.5 Death, obituaries, vital indexes

| Code | Description | Typical sources |
| --- | --- | --- |
| `obituary` | Obituary text / memorial biography | Newspapers, legacy/obituary aggregators, funeral homes |
| `death_notice` | Short death notice | Newspapers, funeral homes |
| `funeral_notice` | Service time/place notice | Funeral homes, papers |
| `vital_death_index` | Public death index / SSDI-style public index where available | State vital indexes that are public; genealogical death indexes **as discovery only unless authoritative** |
| `medical_examiner_case` | Public ME case summary | County ME public pages |

Obituaries are **outcome-class leads**. They require name + age/DOB + geography
+ chronology corroboration; they are not automatic identification.

### 2.6 News, archives, publishing, and discovery

| Code | Description | Typical sources |
| --- | --- | --- |
| `news_missing_report` | Current news coverage of missing person | Local/regional news |
| `news_crime_report` | Crime / arrest / court / homicide reporting | Local/regional news, wire |
| `news_identification` | “Identified as…” remains or victim stories | News + official release cross-check |
| `newspaper_archive_hit` | Hit in **old newspaper** / backfile OCR | Chronicling America–class corpora, regional archives, licensed newspaper APIs |
| `historical_publication` | Book, pamphlet, county history, published notice | Library catalogs, digital book archives |
| `periodical_clipping` | Magazine / gazette / periodical clip | Periodical indexes, police-gazette–style archives |
| `library_digital_collection` | Library-hosted digital collection item | University / public library digital collections |
| `archive_missing_report` | Historical missing story in archives | Newspaper archives |
| `archive_crime_report` | Historical crime / Doe / homicide clip | Newspaper archives |
| `archive_obituary` | Obituary found in newspaper backfiles | Newspaper archives |
| `discovery_lead` | Search engine / aggregator / people-index hit | Google/Bing/caches, public people finders, inmate aggregators |

Discovery leads never confirm identity alone. Aggregator inmate/court copies
collapse into the provenance family of the underlying authoritative record when
detectable. Archive **publication** dates must not be conflated with event dates.

---

## 3. Source classes by adapter family

Implement adapters as families. A deployment enables families under ToS and
jurisdictional need.

### A. Missing-person registries and clearinghouses

- National / state missing-person public portals
- NamUs public missing and unidentified (and authorized partner APIs when held)
- Sheriff / police public missing-person pages
- Nonprofit clearinghouses with public case pages
- Tribal / regional public missing resources where available

**Emits:** `missing_person_notice`, `missing_person_update`, `unidentified_remains`, `found_person_notice`

### B. Arrest, booking, and jail

- County sheriff inmate search / roster
- Regional jail and city lockup public portals
- Multi-county jail consortium sites
- Public arrest logs / blotters

**Emits:** `arrest`, `booking`, `custody`, `release`

### C. Corrections / DOC

- State department of corrections inmate locators
- Federal public inmate locator (where terms allow programmatic use)

**Emits:** `incarceration`, `release` (if published)

### D. Courts and dockets

- State judiciary public access (e.g. Odyssey Public Access and equivalents)
- County clerk criminal/civil indexes
- Municipal court calendars
- Appellate public dockets
- Authorized PACER / equivalent for users with lawful credentials

**Emits:** `charge`, `court_filing`, `hearing`, `disposition`, `appeal`, sometimes `warrant_public`

### E. Crime open data and blotters

- City/county open-data crime incident feeds
- Published police logs
- Agency blotter PDFs / HTML

**Emits:** `crime_incident` (often without full names — still useful for
jurisdiction-time anchors when names appear)

### F. Homicide / violent-crime public releases

- Police / sheriff homicide investigation press releases
- Medical examiner public case / Doe pages
- Cold-case public pages

**Emits:** `homicide_victim`, `homicide_suspect_mention`, `unidentified_remains`, `public_tip_or_release`

### G. Obituaries and death notices

- Newspaper obituary sections and archives
- Funeral home listings
- Major obituary aggregators (discovery / death_remembrance tier)
- Public memorial pages

**Emits:** `obituary`, `death_notice`, `funeral_notice`

### H. Vital and death indexes (public subset only)

- State public death indexes where published
- Genealogical death indexes as **discovery** unless statute/policy makes them authoritative for the use case

**Emits:** `vital_death_index`

### I. News (current)

- Local news crime / courts / missing desks
- Wire stories that cite official releases

**Emits:** `news_missing_report`, `news_crime_report`, `news_identification`, and role-tagged homicide/arrest mentions

### I2. Newspaper archives, libraries, and publishing

- Historical newspaper archives (regional and national backfiles)
- Library digital newspaper collections (Chronicling America–class and peers)
- Licensed OCR newspaper APIs / dumps under ToS
- Periodical and magazine indexes; historical crime gazettes
- Published pamphlets, county histories, true-crime books (usually discovery tier)
- Genealogical news-clip mirrors (discovery unless original paper provenance is clear)

**Emits:** `newspaper_archive_hit`, `library_digital_collection`, `periodical_clipping`,
`historical_publication`, `archive_missing_report`, `archive_crime_report`, `archive_obituary`

See [cold-case-archives.md](cold-case-archives.md).

### I3. Cold-case Doe / unidentified

- NamUs Unidentified (public + authorized professional when held)
- County medical examiner public Doe / unidentified pages
- State unidentified / cold-case clearinghouses
- Agency cold-case public listings
- Archive clippings describing unidentified remains

**Emits:** `john_doe_notice`, `jane_doe_notice`, `unidentified_remains`,
`cold_case_unidentified`, `medical_examiner_case`, `news_identification`

### J. Discovery layer

- Web search APIs (terms-compliant)
- Cached pages
- Public people indexes / record aggregators
- Meta-inmate / meta-court scrapers that only republish public pages

**Emits:** `discovery_lead` (and provisional other classes marked `original_or_derivative=derivative`)

### K. Authorized institutional (operator credentials only)

- LE RMS / CAD exports the operator is entitled to use
- Prosecutor / advocate case systems under agreement
- Partner APIs (NamUs professional, etc.)

**Emits:** any event class the authorization covers. Access basis = `authorized`.
Never impersonate or bypass.

---

## 4. Minimum adapter set for MVP

| Priority | Adapter family | Why |
| --- | --- | --- |
| P0 | Missing-person public notice | Direct case class |
| P0 | Jail booking / inmate search (one multi-county or one large county) | Highest-yield institutional contact |
| P0 | Court public docket (one state or one large county) | Independent corroboration of booking |
| P0 | Obituary / death notice (one aggregator or regional papers) | Death-outcome class |
| P1 | News crime / missing search | Independent reporting + homicide/arrest mentions |
| P1 | **Newspaper / library archive adapter** | Old publishing + cold-case clips |
| P1 | **Doe / unidentified (John & Jane)** | Cold-case remains matching options |
| P1 | DOC inmate locator (state of last known residence) | Longer custody window |
| P2 | Open-data crime incidents | Geographic-temporal scaffolding |
| P2 | Discovery web search | Lead generation only |

---

## 5. Query families by event class

Templates the Query Planner should emit (identity tokens + jurisdiction + time
window substituted at runtime):

**Missing**

```
("{name}" OR {aliases}) {jurisdiction} (missing OR "endangered missing" OR "last seen")
```

**Arrest / booking**

```
("{name}" OR {aliases}) {jurisdiction} (arrest OR booking OR inmate OR jail OR custody)
```

**Court**

```
("{name}" OR {aliases}) {jurisdiction} (court OR docket OR "case number" OR hearing OR charged)
```

**Homicide / violent crime**

```
("{name}" OR {aliases}) {jurisdiction} (homicide OR murder OR "homicide victim" OR "identified as" OR "person of interest")
```

**Obituary / death**

```
("{name}" OR {aliases}) (obituary OR "death notice" OR "passed away" OR funeral) {jurisdiction_or_region}
```

**Unidentified remains / Doe**

```
(unidentified OR "Jane Doe" OR "John Doe" OR "unknown female" OR "unknown male")
{jurisdiction} ({age_band} OR {sex} OR {date_window})
```

**Old newspapers / archives**

```
("{name}" OR {aliases}) ({year_from}-{year_to} OR {decade})
(newspaper OR "news archive" OR microfilm OR "digital collection")
{jurisdiction} (missing OR arrested OR court OR homicide OR unidentified)
```

**Historical publishing**

```
("{name}" OR {aliases}) (magazine OR periodical OR gazette OR pamphlet OR yearbook)
{jurisdiction_or_region}
```

After a high-value ID appears, collapse to identifier-centric queries regardless
of event class.

Full mode definitions: [cold-case-archives.md](cold-case-archives.md).

---

## 6. Normalization rules unique to sensitive classes

1. **Date kind required** — never store a bare date without
   `arrest|booking|filing|hearing|publication|death|service|retrieval|unknown`.
2. **Role required** on crime/homicide/news records.
3. **Obituary age vs subject DOB** — compute age-on-death-date compatibility;
   mismatch is a major contradiction.
4. **Homicide victim identification** — prefer agency release over news alone;
   news without release stays `independent_reporting` / investigate.
5. **Warrant lists** — only where the agency publishes them for public
   consumption; still not confirmation of identity match without corroboration.
6. **Unidentified remains / Doe** — score as biological/demographic compatibility
   leads; never auto-merge to subject without authoritative ID process. Prefer
   `john_doe_notice` / `jane_doe_notice` when sex is stated on the source.
7. **Archive publication dates** — store as `publication`; do not treat print day
   as arrest/death/last-seen unless the article states that event date.
8. **Derivative aggregators** — set `original_or_derivative=derivative` and
   attempt provenance clustering to the originating jail/court/paper URL when present.

---

## 7. Coverage honesty

For each case report, list:

- Event classes searched
- Adapters run / failed / skipped
- Jurisdictions with zero coverage
- Dead-end certificates issued
- Whether absence of an obituary or arrest hit is **informative** (coverage high)
  or **unknown** (coverage low)

---

## 8. Out of scope for adapters

- Stolen credentials or session hijacking
- Dark-web markets or illicit data brokers
- Non-consensual continuous GPS / phone location streams
- Private social DMs, cloud backups, or sealed records without lawful process
- Automated doxxing or public accusation feeds

If a data source cannot be accessed lawfully under the case’s eligibility basis,
the adapter must refuse with a visible `access_denied` coverage entry — not
fail open.
