# M.I.A.Lock | Concept and Software Design Whitepaper | v1.1

**Missing Individual Autonomous Lock**

AI-assisted missing-person discovery, identity correlation, evidence provenance,
and historical movement reconstruction

Version 1.1 | September 2026

> Search broadly. Match probabilistically. Challenge every hit. Preserve provenance. Verify before action.

---

## Executive Summary

M.I.A.Lock is a proposed privacy-bounded software system for legitimate
missing-person searches. It converts incomplete identity information into a
versioned search fingerprint, autonomously queries lawful public or properly
authorized information sources, normalizes discovered records, scores candidate
identity matches, searches for contradictions, and assembles an evidence-backed
historical timeline of where the missing person may have interacted with
institutions or public records.

The system is designed around a critical distinction: **a search hit is not an
identification**. M.I.A.Lock reports a candidate-match score, the evidence
contributing to that score, contradictory evidence, source independence, coverage
gaps, and the next verification step. Location is represented as documented
historical events with uncertainty, not as covert continuous tracking.

**Primary technical contribution:** integration of alias expansion, federated
source adapters across missing-person / crime / arrest / court / death /
obituary and related public-record classes, provenance-aware entity resolution
with name-frequency priors, competing-hypothesis scoring, contradiction testing,
negative-evidence certificates, calibrated confidence, recursive query
generation, temporal-geographic graphing, eligibility gates, and human
verification into a single auditable workflow.

---

## 1. Use Case and Design Problem

Missing-person searches are difficult because relevant records are fragmented by
jurisdiction and record type. The same individual may appear under a legal name,
former surname, nickname, abbreviation, misspelling, booking alias, partial date
of birth, or outdated address. A search engine can return hundreds of same-name
records while missing the one record that matters.

Outcomes that resolve or reframe a missing-person case are also fragmented:
arrests and bookings, court appearances, custody and release, homicide victim or
suspect mentions in public releases, unidentified remains notices, obituaries,
death notices, and news crime reports. M.I.A.Lock treats these as **event
classes** under one evidence pipeline — not as separate products.

M.I.A.Lock answers four questions:

1. Is this record plausibly the same person?
2. How independent and authoritative is the evidence?
3. When and where does the record place the person?
4. What evidence would confirm or falsify the match?

### 1.1 Core requirements

- Accept partial and uncertain identity information without silently converting
  uncertainty into fact.
- Enforce **case eligibility** and role gates before autonomous search or Watch Mode.
- Generate evidence-supported aliases and query variants with speculative-debt caps.
- Search multiple jurisdictions and source classes through modular adapters —
  including missing-person registries, arrests, crimes, murders/homicides,
  courts, corrections, obituaries, and related lawful public records (see
  [source-catalog.md](source-catalog.md)).
- Preserve raw source provenance and distinguish original records from copies.
- Score candidates using matching evidence, contradictory evidence, **population
  priors**, and **provenance independence**.
- Maintain **competing identity hypotheses**, not only a flat ranked list.
- Represent time and geography probabilistically; emit **coverage maps** and
  **dead-end certificates** when searches find nothing.
- Use new identifiers to drive bounded, information-gain follow-up searches.
- Support recurring checks for unresolved legitimate cases.
- Require human or authoritative verification before consequential action.

### 1.2 Hard non-goals

- Continuous live-location tracking of private individuals.
- Social-graph stalking or unrestricted associate mapping as a product feature.
- Scraping or simulating restricted law-enforcement systems without lawful
  authorization.
- Credential theft, impersonation, social engineering, or access-control bypass.
- Automated police dispatch, public accusation, or media naming from an AI score.
- Treating ranking scores as calibrated probabilities before empirical validation.

---

## 2. Conceptual Architecture

```
[Eligibility Gate / Case Intake]
            |
            v
[Identity Fingerprint] ---> [Alias / Variant Engine]
            |                         |
            +------------+------------+
                         v
                 [Query Planner]
                 (information gain)
                         |
        +----------------+----------------+
        |                |                |
        v                v                v
   Source adapters  (by event class / jurisdiction)
   missing | arrest | crime | homicide | court |
   custody | obit | death | news | discovery
        |                |                |
        +----------------+----------------+
                         v
              [Evidence Normalizer]
                         |
                         v
           [Provenance / Dedup Graph]
                         |
                         v
            [Identity Correlator]
               /              \
              v                v
      [Match + Priors]   [Contradiction Engine]
               \              /
                v            v
          [Hypothesis Ledger]
                         |
                         v
        [Temporal-Geographic Event Graph]
           + coverage / negative evidence
                /                    \
               v                      v
      [Recursive Search]        [Human Review]
               \                      /
                +----------+----------+
                           v
                  [Verified Outcome]
                  (DecisionGATE before escalate/export)
```

---

## 3. Eligibility, Roles, and Purpose Binding

Every case declares a **purpose** (legitimate missing person; authorized
investigation under stated authority). The Case Manager refuses or quarantines
intake that fails eligibility checks.

| Role | Capabilities |
| --- | --- |
| Intake | Open case, attach attestation / authorization basis |
| Analyst | Run searches, review candidates, request verification |
| Supervisor | Approve Watch Mode, exports, escalation |
| Auditor | Read-only access to audit trail and coverage reports |

**DecisionGATE integration (recommended):** before Watch Mode, export, or
external escalation, run a sequential ethical filter (PASS / REVISE / BLOCK).
Autonomy may discover; humans authorize consequential next steps.

---

## 4. Identity Fingerprint

Every case begins with a versioned Subject Fingerprint. Each attribute stores
value, confidence, source, date learned, and state:
`confirmed | probable | reported | rejected`.

```
SubjectFingerprint {
  subject_id
  canonical_name
  aliases[]                  # evidence-backed; speculative marked separately
  date_of_birth {exact|range|partial|unknown}
  expected_age(event_date)
  sex_descriptor
  historical_jurisdictions[]
  event_anchors[]            # last-seen, reported places, known contacts (lawful)
  known_record_ids[]
  rejected_candidates[]
  population_priors {
    name_frequency_band      # rare | uncommon | common | very_common
    dob_specificity
    jurisdiction_size_band
  }
  speculative_alias_debt     # fraction of score dependent on unverified aliases
  evidence_version
}
```

Aliases are not free. A nickname such as Tina for Christina can be a search
variant, but it remains a variant until evidence ties it to the subject.
Former surnames and spelling variants receive stronger status when supported by
records. If speculative alias debt exceeds a configured threshold, the candidate
is auto-quarantined pending grounding.

---

## 5. Query Planning and Autonomous Search

The Query Planner creates combinations of identity, time, geography, record
type, and **event class**. Early search is broad across high-yield event classes
(missing-person notices, arrests/bookings, courts, obituaries). After stronger
evidence appears, queries become specific (case ID, agency, docket).

**Information-gain policy:** prefer queries expected to most reduce identity
entropy (rare identifiers, exact DOB-constrained agency lookups, docket numbers)
over brute-force same-name crawling. Recursion is capped by depth, source policy,
query budget, **expected information value**, and legitimate-case scope.

Example search family (identity + jurisdiction + event class):

```
("Christina Green" OR "Christy Green" OR "Tina Green")
AND Illinois
AND ("2026-08-07" OR "August 7 2026")
AND (arrest OR booking OR court OR custody OR missing OR homicide OR obituary OR "death notice")
```

After a case identifier appears:

```
"<case-id>"
"Tina Green" "<case-id>"
"<agency>" "Tina Green"
"<charge>" "Tina Green" "2026"
```

The software must respect each source's terms, authentication boundaries,
robots/rate controls, and legal access rules. Restricted law-enforcement systems
are not scraped or simulated.

---

## 6. Source Adapter Framework

M.I.A.Lock uses pluggable source adapters rather than one monolithic crawler.
Each adapter implements a common contract and records what it can and cannot
establish. Full taxonomy: [source-catalog.md](source-catalog.md).
Machine-readable types: [schemas/event_types.json](schemas/event_types.json).

```
interface SourceAdapter:
  source_metadata()          # tier, event_classes[], jurisdictions[], coverage
  validate_access()
  build_request(search_job)
  fetch()
  parse()
  normalize()
  provenance_signature()
  rate_limit_policy()
  coverage_report()          # what was actually searchable this run
  error_state()
```

### 6.1 Source tiers

| Tier | Role | Examples |
| --- | --- | --- |
| Authoritative public | Confirmation-capable | Courts, sheriff/jail public portals, corrections, police public releases, government missing-person resources, vital-records indexes where public |
| Authorized institutional | Confirmation under user access | NamUs partner tools, LE case systems the user is lawfully entitled to use |
| Independent reporting | Corroboration / leads | Reputable local news, newspaper archives, public crime blotters |
| Death / remembrance | Outcome class | Obituaries, death notices, funeral home listings, public memorial pages |
| Discovery | Leads only | Search engines, cached pages, public aggregators and people indexes |

Discovery sources generate leads rather than confirmation. Aggregator copies of
the same underlying booking or docket collapse to one provenance family.

### 6.2 Event classes the system must track

Every adapter declares which **event classes** it can emit. The pipeline is
incomplete if it cannot represent the classes that commonly resolve or reframe
missing-person cases:

| Event class | Why it matters for missing persons |
| --- | --- |
| `missing_person_notice` | Active / historical missing reports, posters, registries |
| `unidentified_remains` | Possible match to Jane/John Doe notices |
| `arrest` / `booking` | Custody contact; often first public institutional hit |
| `charge` / `court_filing` / `hearing` / `disposition` | Identity + chronology anchors |
| `custody` / `release` / `incarceration` | Location-at-time institutional presence |
| `crime_incident` | Victim/witness/suspect mentions in public blotters (role-tagged) |
| `homicide_victim` / `homicide_suspect_mention` | Critical outcome / lead classes from public releases only |
| `warrant_public` | Public warrant notices where lawfully published |
| `obituary` / `death_notice` / `funeral_notice` | Possible death outcome; requires careful identity scoring |
| `vital_death_index` | Public death-index hits where available |
| `news_crime_report` | Independent reporting of crime / missing / identified remains |
| `public_tip_or_release` | Official LE public information releases |
| `discovery_lead` | Aggregator / search-engine hits (never confirmation alone) |

Role on a crime record (`subject_as_missing` | `victim` | `suspect_mention` |
`witness_mention` | `unspecified`) is stored explicitly so a news hit naming
someone as a homicide victim is not scored as if they were booked as a suspect.

---

## 7. Evidence Normalization

Every raw result becomes a normalized Evidence object while retaining the
original source reference. **Date typing is a hard invariant:** arrest date,
booking date, filing date, publication date, hearing date, death date, service
date, and retrieval date are not interchangeable. Conflating them is a scoring
failure mode, not a soft penalty.

```
Evidence {
  evidence_id
  source_id
  source_tier
  event_class
  subject_role_on_record
  original_or_derivative
  retrieved_at
  event_dates[]              # each typed: arrest|booking|filing|hearing|...
  names[]
  dob_or_age
  jurisdiction
  agency
  case_or_booking_id
  charges_or_event_type[]
  status
  raw_reference
  content_hash
  access_basis               # public | authorized | attested
}
```

---

## 8. Provenance and Echo Detection

M.I.A.Lock must not count copied records as independent confirmation. The
Provenance Graph clusters evidence that appears to originate from the same
underlying record. A sheriff feed reproduced by two aggregators and a search
cache is **one evidence lineage**; a sheriff booking plus a separate court
docket can be independent.

Provenance independence is a scoring feature. This prevents artificial
confidence inflation from repeated copies of the same erroneous source.
Source-trust may decay when aggregators conflict with authoritative originals.

---

## 9. Identity Correlation Model

### 9.1 Interpretable ranking (MVP)

```
S_rank = 100 * (sum(w_i * m_i) - sum(p_j * c_j)) / sum(w_i)
```

`S_rank` is a **candidate-ranking score**. It must not be labeled as the
probability that the candidate is the missing person unless calibrated against
labeled cases.

### 9.2 Population priors

Common attributes are down-weighted; rare identifiers are up-weighted:

- Exact DOB + rare alias + matching event date ≫ common name + state.
- Name-frequency band and jurisdiction size enter as prior features.
- Same-name twin risk is tracked explicitly for common names.

### 9.3 Likelihood ratios (mature)

```
LR = P(Evidence | same_person) / P(Evidence | different_person)
```

### 9.4 Competing hypotheses

Candidates are maintained as **mutually exclusive identity hypotheses** when
they cannot all be the same person. When one hypothesis gains independent
authoritative support, competing hypotheses are down-weighted or rejected.
The ledger stores hypothesis sets, not only independent rows.

### 9.5 Feature families

- Name similarity: exact, nickname, former surname, edit distance, phonetic.
- Demographics: DOB, age-on-event-date, sex descriptor where lawfully available.
- Temporal: typed event-date compatibility and chronology.
- Geographic: reported state/county and historical jurisdiction compatibility.
- Record linkage: case/booking numbers, agency, other lawful identifiers.
- Event-class fit: missing notice vs arrest vs obituary vs homicide mention.
- Source quality and provenance independence.
- Contradictions and speculative-alias debt.
- Population priors / same-name collision risk.

### 9.6 Counterfactual explanation (review UX)

For each strong candidate, the Review Console can show: which feature removal
would drop the score below the investigate threshold. Next-verification steps
are the primary UI output; rank score is secondary.

---

## 10. Contradiction Engine

Every strong candidate triggers an adversarial pass whose purpose is to
**disprove** the match.

```
if exact_dob_conflict:
    quarantine(candidate)
elif strong_identity_conflict:
    apply_major_penalty(candidate)
elif speculative_alias_debt > threshold and no grounding record:
    quarantine(candidate)
else:
    continue_verification(candidate)
```

A candidate may lose confidence as the system learns more. This is intentional.
M.I.A.Lock converges toward the best-supported identity rather than defending
its first plausible hit.

---

## 11. Temporal-Geographic Event Graph

The Event Graph represents documented historical contact points. Each node has
a time interval (soft uncertainty band), jurisdiction, source, candidate
identity score, geographic confidence, event class, and verification state.
Unknown intervals remain **UNKNOWN**.

```
[Known location A]
        |
        v
[Reported event - unverified]
        |
        v
[Official court / booking event - verified]
        |
        v
[Release / disposition / death notice if documented]
        |
        v
[UNKNOWN]
```

The system may expand searches around a verified jurisdiction. It does **not**
infer a person's current location from a historical record.

**TrajectoryLock (optional):** geometric consistency checks apply only to
*verified* event nodes. No extrapolated travel paths between UNKNOWN gaps.

### 11.1 Coverage maps and negative evidence

Absence of evidence, when search coverage is known, is itself evidence:

```
DeadEndCertificate {
  case_id
  source_id
  event_classes_searched[]
  jurisdiction
  time_window
  query_spec
  coverage_estimate        # fraction of expected corpus reachable
  result: zero_compatible_hits
  retrieved_at
}
```

Case reports must show sources attempted, sources failed, and jurisdictions not
covered. Silent gaps are treated as first-class failure visibility.

---

## 12. Recursive Search Engine

```
def expand(candidate):
    new_terms = extract_high_value_identifiers(candidate)
    for term in new_terms:
        if not previously_searched(term) and within_scope(term):
            if expected_information_gain(term) >= min_gain:
                enqueue(term, depth=candidate.depth + 1)
```

High-value identifiers include case numbers, agency names, charges, court
divisions, exact event dates, booking IDs, and public record identifiers.
Recursion prefers information gain over brute-force crawling.

---

## 13. Candidate Confidence Presentation

| Range | Label | Meaning |
| --- | ---: | --- |
| 0–29 | Noise | Insufficient compatibility |
| 30–49 | Weak candidate | Retain only if search space is sparse |
| 50–69 | Investigate | Worth targeted verification |
| 70–84 | Strong candidate | Multiple compatible signals |
| 85–94 | Probable candidate | High-priority human verification |
| 95–99 | Near-certain correlation | Still requires authoritative confirmation |
| 100 | Confirmed | Reserved for authoritative identity confirmation |

Before empirical calibration, these ranges are **operational ranking labels**,
not measured probabilities. The UI and export template must show calibration
status explicitly. Never present uncalibrated ranks as percentages of identity.

**Primary output field:** next verification step (cheapest falsifying check).

---

## 14. Watch Mode

For an unresolved legitimate missing-person case, Watch Mode periodically
reruns unresolved high-value searches and checks known candidate records for
material changes. It suppresses duplicates and alerts only when new evidence
changes candidate or hypothesis state.

```
watch_cycle(case):
    refresh_high_value_sources()
    detect_new_or_changed_records()
    normalize_and_deduplicate()
    rescore_hypotheses()
    update_event_graph_and_coverage()
    alert_if_material_change()
```

Requires supervisor approval. Scheduler supports per-source cadence, exponential
backoff, failure logging, and case-level stop conditions. Monitoring terminates
when the search purpose ends or an authorized reviewer closes the case.

---

## 15. Software Components

- **Case Manager** — intake, eligibility, case state, authorization, closure
- **Fingerprint Service** — canonical facts, aliases, priors, evidence states
- **Query Planner** — controlled fan-out, information gain, recursion budgets
- **Adapter Runtime** — source-specific fetch/parsing by event class
- **Normalizer** — schema mapping, date typing, role tagging, field extraction
- **Evidence Store** — immutable raw references, hashes, normalized records
- **Provenance Graph** — duplicate and source-lineage detection
- **Correlation Service** — ranking, priors, hypothesis sets, later calibration
- **Contradiction Service** — active falsification and identity-conflict detection
- **Event Graph** — temporal/geographic reconstruction + coverage/dead-ends
- **Review Console** — comparison, counterfactuals, source inspection, decisions
- **Watch Scheduler** — recurring searches and change detection
- **Audit Service** — query, access, scoring, review, and export logs
- **Export / Language Guard** — confirmed vs inferred vs unresolved; GlossaFilter optional

---

## 16. Reference Database Schema

```
cases(case_id, status, purpose, eligibility_basis, created_at, closed_at)
subjects(subject_id, case_id, canonical_name, dob_min, dob_max, sex,
         name_frequency_band)
aliases(alias_id, subject_id, alias_text, alias_type, confidence,
        evidence_id, speculative)
sources(source_id, name, tier, authority_level, access_basis,
        event_classes[], jurisdictions[])
evidence(evidence_id, source_id, event_class, subject_role, retrieved_at,
         content_hash, raw_reference, provenance_cluster, access_basis)
records(record_id, evidence_id, name, dob, age, event_type, event_at,
        event_date_kind, jurisdiction, agency, external_record_id, status)
candidates(candidate_id, subject_id, record_id, hypothesis_set_id,
           rank_score, calibrated_probability, review_state,
           speculative_alias_debt)
features(candidate_id, feature_name, expected_value, observed_value,
         contribution)
contradictions(contradiction_id, candidate_id, type, severity, evidence_id)
events(event_id, candidate_id, event_class, start_at, end_at, jurisdiction,
       geo_confidence, verification_state)
dead_ends(certificate_id, case_id, source_id, jurisdiction, time_window,
          event_classes[], coverage_estimate, retrieved_at)
reviews(review_id, candidate_id, reviewer_id, decision, notes, reviewed_at)
search_jobs(job_id, case_id, source_id, query_spec, recursion_depth,
            expected_gain, status, started_at, completed_at)
audit_log(entry_id, actor, action, case_id, payload_hash, at)
```

---

## 17. API Design

```
POST   /cases
GET    /cases/{id}
POST   /cases/{id}/aliases
POST   /cases/{id}/anchors
POST   /cases/{id}/search
GET    /cases/{id}/candidates
GET    /cases/{id}/hypotheses
GET    /cases/{id}/coverage
GET    /candidates/{id}/evidence
GET    /candidates/{id}/counterfactual
POST   /candidates/{id}/review
GET    /cases/{id}/timeline
POST   /cases/{id}/watch          # supervisor-gated
DELETE /cases/{id}/watch
POST   /cases/{id}/export         # supervisor-gated; marks fact vs inference
POST   /cases/{id}/close
```

Write operations are authenticated and auditable. Source credentials, where
required and legitimately held, live in a secrets manager — never in query logs
or exported reports.

---

## 18. Reference Processing Pipeline

```
def run_case(case_id):
    case = load_case(case_id)
    assert eligibility_gate(case)
    fp = fingerprint_service.build(case)
    jobs = query_planner.plan(fp)  # across event classes in source catalog
    for job in jobs:
        raw_items, coverage = adapter_runtime.execute(job)
        coverage_store.save(coverage)
        if not raw_items:
            dead_ends.save(job, coverage)
            continue
        for raw in raw_items:
            evidence = evidence_store.persist_raw(raw)
            record = normalizer.normalize(evidence)
            provenance_graph.attach(record)
            candidate = correlator.compare(fp, record)
            contradictions = contradiction_service.test(fp, candidate)
            score = correlator.rescore(
                candidate,
                contradictions,
                provenance_graph.independence(candidate),
                fp.population_priors,
            )
            hypothesis_ledger.save(score)
            event_graph.update(candidate)
            if candidate.has_new_identifiers:
                query_planner.enqueue_followups(candidate)
            if score >= REVIEW_THRESHOLD:
                review_console.queue(candidate)
```

---

## 19. Security, Privacy, and Abuse Controls

M.I.A.Lock must remain purpose-bound. Its architecture supports legitimate
missing-person searches and authorized investigations without becoming a
generalized stalking or covert surveillance product.

- No credential theft, impersonation, social engineering, account compromise,
  or bypassing access controls.
- No acquisition or use of illicit location data or unauthorized private
  communications.
- No unrestricted continuous live-location tracking of private individuals.
- No scraping of restricted law-enforcement systems without lawful authorization.
- No automated police dispatch, public accusation, or other consequential action
  solely from an AI score.
- Encryption at rest and in transit for sensitive case data.
- Role-based access control, immutable audit logging, query-rate controls,
  retention limits, and mandatory case close/stop state.
- Exported reports distinguish confirmed facts, candidate inferences, and
  unresolved claims.
- Crime/homicide-related public records are ingested only as **leads or
  documented events** with explicit subject role tags — never as automatic guilt
  or identification conclusions.

---

## 20. Validation and Calibration

Validate on resolved historical cases using only information available at the
simulated search start time (time-travel evaluation). Separate development and
held-out cases.

Required metrics:

- Top-k correct-record retrieval
- Precision / recall of identity resolution
- **False-merge rate on same-name twins** (headline stress metric)
- False-positive rate for common names
- Calibration error of confidence values (when calibrated)
- Time to first correct lead
- Performance under wrong/missing DOB, surname, county, or date
- Provenance deduplication effectiveness
- Contradiction-engine rejection accuracy
- Dead-end / coverage reporting accuracy
- Human reviewer agreement and override rates
- Search coverage and source failure rates
- Event-class recall (arrest vs court vs obituary vs missing notice)

---

## 21. Failure Modes

- False merge of two people with similar names
- False negative from a non-indexed jurisdiction
- Copied-source echo mistaken for independent confirmation
- Stale address treated as present location
- Arrest, booking, filing, hearing, publication, and death dates conflated
- Incorrect family report treated as authoritative fact
- Alias expansion becoming speculative
- Ranking score misrepresented as probability
- Recursive search drifting beyond legitimate case purpose
- Source changes breaking parsers or silently reducing coverage
- Obituary / homicide news hit over-trusted without identity corroboration
- Role confusion (victim vs suspect mention vs missing subject)

The software should fail visibly. Adapter outages, inaccessible sources, missing
jurisdictions, parser errors, and unresolved ambiguity must appear in the case
report rather than being silently ignored.

---

## 22. Deployment Model

Practical deployment: web review console, REST API, background worker queue,
relational database, optional graph layer, object storage for evidence snapshots
where lawful, and a scheduler for Watch Mode.

```
Web / Mobile Review UI
          |
     API Gateway
          |
  +-------+--------+----------------+
  |       |        |                |
Case API  Search Workers   Review Service
  |       |        |                |
PostgreSQL  Adapter Pool   Candidate / Hypothesis Ledger
  |                |
  +---- Provenance / Event Graph / Coverage
                 |
        Evidence Object Store
                 |
           Audit / Metrics
```

A small initial build can use PostgreSQL for relational data and graph-like
edges, a task queue for search jobs, and containerized adapters. Dedicated graph
infrastructure is optional until scale justifies it.

---

## 23. Development Roadmap

1. **Milestone 1** — Eligibility/auth roles, case intake, fingerprint schema,
   alias management, manual evidence entry.
2. **Milestone 2** — Query planner, public-source adapters across core event
   classes (missing, arrest/booking, court, obituary/death notice, news crime),
   normalized evidence, immutable provenance, coverage reports.
3. **Milestone 3** — Deterministic scoring with priors, contradiction engine,
   competing hypotheses.
4. **Milestone 4** — Review console (next-verification first), counterfactuals,
   temporal-geographic event graph, dead-end certificates.
5. **Milestone 5** — Recursive query generation (information gain) and
   supervisor-gated Watch Mode.
6. **Milestone 6** — Labeled-case calibration, twin-collision evaluation,
   probabilistic scoring.
7. **Milestone 7** — Security hardening, abuse testing, retention policy,
   DecisionGATE on export/escalate, external review.
8. **Milestone 8** — Controlled pilot with investigators, advocates, or
   authorized missing-person organizations.

---

## 24. Minimum Viable Product

The MVP deliberately avoids every source. It needs enough functionality to prove
the architecture:

- Case intake + eligibility
- Evidence-supported aliases
- Adapters for at least: one missing-person public resource class, one
  arrest/booking or court class, one obituary/death-notice class, one news
  crime/discovery class
- Immutable source capture and provenance clustering
- Deterministic scoring with priors + contradiction flags
- Candidate comparison with next-verification prompts
- Event timeline + coverage / dead-end visibility
- Manual verification

Success is not measured by pages crawled. It is measured by whether the system
reliably raises the correct record above same-name noise, explains why, surfaces
coverage gaps, and exposes enough provenance for a human to verify the lead.

---

## 25. Conclusion

M.I.A.Lock proposes a defensible software architecture for AI-assisted
missing-person searches. Its central principle is **evidence locking**: every
candidate identity, event, and geographic inference remains attached to its
source, confidence, contradictions, coverage context, and verification state.

The system combines autonomous discovery across the lawful public record surface
that actually resolves missing-person cases — registries, arrests, crimes,
homicides, courts, custody, obituaries, and related notices — with deliberate
skepticism. It can discover a weak alias hit, combine it with age, date and
jurisdiction, identify independent corroboration, reconstruct an evidence-backed
historical path, certify where it searched and found nothing, and recommend the
next verification step. It must also be capable of saying that the evidence is
insufficient or contradictory.

That combination — autonomous discovery plus provenance, falsification,
uncertainty, coverage honesty, and human verification — is the foundation for a
missing-person search system that can scale without treating search-engine
coincidence as identity.

---

## Appendix A — Candidate Report Format

```
M.I.A.Lock Candidate Lead
Candidate: [display name]
Rank score: [0-99]
Calibration status: [uncalibrated / calibrated]
Verification: [unverified / probable / verified / rejected]
Event class: [arrest | court | obituary | missing_notice | ...]
Subject role on record: [missing | victim | suspect_mention | ...]

NEXT VERIFICATION (primary)
- [cheapest falsifying authoritative check]

MATCHING SIGNALS
- Name / alias relationship
- DOB / age
- Event date (typed)
- Jurisdiction
- Record identifiers
- Prior band (name frequency)

CONTRADICTIONS
- None found / list

PROVENANCE
- Independent source families
- Authoritative sources
- Derivative sources

TIMELINE EFFECT
- Earliest supported event
- Latest supported event
- Geographic confidence
- Coverage / dead-ends affecting this window

DO NOT INTERPRET AS CONFIRMED IDENTITY UNTIL VERIFIED.
```

---

## Appendix B — Design Principles

1. Evidence before inference.
2. Unknown is a valid state.
3. One copied record is still one source.
4. Every strong hit deserves a falsification attempt.
5. Historical location evidence is not live tracking.
6. Confidence must be calibrated or clearly labeled as ranking.
7. Autonomy may discover; humans verify consequential conclusions.
8. Every search, score, and decision should be auditable.
9. Coverage gaps and zero-hit searches must be visible.
10. Event class and subject role are first-class — never collapse “mentioned in
    crime news” into “identified.”
