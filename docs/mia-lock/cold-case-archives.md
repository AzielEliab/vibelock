# Cold cases, archives, and Doe options

M.I.A.Lock search modes for long-horizon and unidentified matching.

## Search modes

| Mode ID | Use when |
| --- | --- |
| `active` | Recent missing-person case; current registries, bookings, courts, news |
| `archives` | Need **old newspapers**, library digital collections, periodicals, publishing archives |
| `doe_cold` | Cold-case match against **John Doe / Jane Doe / unidentified remains** |
| `cold_missing` | Long-term missing: registries + archives + Doe cross-match |
| `all` | Map view only — show every pin for the subject |

Machine implementation: `mialock.search_options` · CLI:
`python -m mialock search-options` · `python -m mialock queries doe_cold`

## Archive & publishing sources

Adapters should cover (ToS-compliant / licensed access):

- Historical newspaper archives (regional + national)
- Library digital newspaper collections (e.g. Chronicling America–class corpora)
- Microfilm / OCR newspaper indexes where lawfully available via API or licensed dump
- Periodical and magazine indexes; police gazette–style historical crime periodicals
- Published true-crime / pamphlet / county history mentions (discovery tier)
- Archived obituaries and death notices inside newspaper backfiles
- Genealogical news-clip mirrors as **discovery** unless provenance to an original paper is clear

**Date typing:** archive **publication date** ≠ arrest/death/last-seen date. Always store
`event_date_kind=publication` when the clip date is the print date.

## John Doe / Jane Doe cold-case options

| Event class | Meaning |
| --- | --- |
| `john_doe_notice` | Public unidentified male Doe notice |
| `jane_doe_notice` | Public unidentified female Doe notice |
| `unidentified_remains` | Unidentified deceased / clearinghouse record |
| `cold_case_unidentified` | Explicit cold-case unidentified listing |
| `cold_case_missing` | Long-term / cold missing-person listing |
| `medical_examiner_case` | Public ME case summary |
| `news_identification` | Later “identified as…” reporting |

**Hard rule:** Doe hits are **compatibility leads** (age band, sex, jurisdiction,
date window, distinguishing marks). Never auto-merge a Doe record into a named
subject fingerprint. Confirmation requires an authoritative identification process.

## Query examples

**Old newspapers**

```
("Christina Green" OR "Christy Green") (1990-1999 OR 1990s)
(newspaper OR "news archive" OR microfilm) Illinois
(missing OR arrested OR court OR homicide OR unidentified)
```

**Jane Doe**

```
("Jane Doe" OR "unidentified female" OR "unknown female")
Cook (20-30 OR female OR 1994 OR tattoo)
```

**John Doe**

```
("John Doe" OR "unidentified male" OR "unknown male")
Milwaukee (25-35 OR male OR 2025)
```

## Map UI

In the person event map, choose **Search mode** to filter pins and show the
query families for that mode. Archive and Doe pins use distinct colors.
