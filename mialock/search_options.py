"""Search modes for active cases, cold cases, archives, and Doe matching.

Generates query families for newspaper/publishing archives and
John Doe / Jane Doe unidentified cold-case options. These are search
plans only — hits remain unverified leads until authoritative confirmation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class QueryFamily:
    family_id: str
    title: str
    event_classes: tuple[str, ...]
    template: str
    notes: str = ""


@dataclass(frozen=True)
class SearchMode:
    mode_id: str
    title: str
    summary: str
    event_classes: tuple[str, ...]
    adapter_families: tuple[str, ...]
    query_families: tuple[QueryFamily, ...]
    cold_case: bool = False
    doe_match: bool = False
    archive: bool = False


def _qf(
    family_id: str,
    title: str,
    event_classes: Iterable[str],
    template: str,
    notes: str = "",
) -> QueryFamily:
    return QueryFamily(
        family_id=family_id,
        title=title,
        event_classes=tuple(event_classes),
        template=template,
        notes=notes,
    )


SEARCH_MODES: dict[str, SearchMode] = {
    "active": SearchMode(
        mode_id="active",
        title="Active missing-person search",
        summary="Current registries, bookings, courts, news, and obituaries.",
        event_classes=(
            "missing_person_notice",
            "missing_person_update",
            "arrest",
            "booking",
            "custody",
            "court_filing",
            "hearing",
            "obituary",
            "news_missing_report",
            "news_crime_report",
            "discovery_lead",
        ),
        adapter_families=(
            "missing_registries",
            "jail_booking",
            "courts",
            "news_current",
            "obituaries",
            "discovery",
        ),
        query_families=(
            _qf(
                "active-missing",
                "Active missing notices",
                ["missing_person_notice", "missing_person_update"],
                '("{name}" OR {aliases}) {jurisdiction} (missing OR "endangered missing" OR "last seen")',
            ),
            _qf(
                "active-booking",
                "Arrest / booking",
                ["arrest", "booking", "custody"],
                '("{name}" OR {aliases}) {jurisdiction} (arrest OR booking OR inmate OR jail OR custody)',
            ),
            _qf(
                "active-court",
                "Court dockets",
                ["court_filing", "hearing", "disposition"],
                '("{name}" OR {aliases}) {jurisdiction} (court OR docket OR hearing OR charged)',
            ),
        ),
    ),
    "archives": SearchMode(
        mode_id="archives",
        title="Archive & old newspaper / publishing search",
        summary=(
            "Historical newspapers, library digital collections, periodical "
            "clippings, and published archives for older mentions."
        ),
        event_classes=(
            "newspaper_archive_hit",
            "historical_publication",
            "periodical_clipping",
            "library_digital_collection",
            "archive_missing_report",
            "archive_crime_report",
            "archive_obituary",
            "news_missing_report",
            "news_crime_report",
            "obituary",
            "discovery_lead",
        ),
        adapter_families=(
            "newspaper_archives",
            "library_digital",
            "periodical_indexes",
            "publishing_archives",
            "genealogy_news_clips",
            "discovery",
        ),
        archive=True,
        query_families=(
            _qf(
                "archive-newspapers",
                "Old newspapers",
                ["newspaper_archive_hit", "archive_missing_report", "archive_crime_report"],
                (
                    '("{name}" OR {aliases}) ({year_from}-{year_to} OR {decade}) '
                    '(newspaper OR "news archive" OR "from the archives" OR microfilm) '
                    '{jurisdiction} (missing OR arrested OR court OR homicide OR unidentified)'
                ),
                notes="Prefer library/digital-archive adapters; publication date ≠ event date.",
            ),
            _qf(
                "archive-publishing",
                "Books / magazines / published notices",
                ["historical_publication", "periodical_clipping"],
                (
                    '("{name}" OR {aliases}) (magazine OR periodical OR gazette OR "police gazette" '
                    'OR pamphlet OR "true crime" OR yearbook) {jurisdiction_or_region}'
                ),
            ),
            _qf(
                "archive-library",
                "Library digital collections",
                ["library_digital_collection", "newspaper_archive_hit"],
                (
                    '("{name}" OR {aliases}) ("digital collection" OR "chronicling america" OR '
                    '"newspaper archive" OR "historical newspapers") {jurisdiction}'
                ),
            ),
            _qf(
                "archive-obits",
                "Archived obituaries / death notices",
                ["archive_obituary", "obituary", "death_notice"],
                (
                    '("{name}" OR {aliases}) (obituary OR "death notice" OR "passed away") '
                    '({year_from} OR {year_to} OR archive) {jurisdiction_or_region}'
                ),
            ),
        ),
    ),
    "doe_cold": SearchMode(
        mode_id="doe_cold",
        title="Cold case — John Doe / Jane Doe unidentified",
        summary=(
            "Match a missing subject against unidentified remains and "
            "public Doe notices (John Doe / Jane Doe / Unknown). "
            "Demographic compatibility only — never auto-identify."
        ),
        event_classes=(
            "unidentified_remains",
            "john_doe_notice",
            "jane_doe_notice",
            "cold_case_unidentified",
            "medical_examiner_case",
            "cold_case_missing",
            "news_identification",
            "archive_crime_report",
            "newspaper_archive_hit",
            "public_tip_or_release",
        ),
        adapter_families=(
            "namus_unidentified",
            "me_doe_pages",
            "cold_case_public",
            "newspaper_archives",
            "news_current",
        ),
        cold_case=True,
        doe_match=True,
        query_families=(
            _qf(
                "doe-jane",
                "Jane Doe notices",
                ["jane_doe_notice", "unidentified_remains", "cold_case_unidentified"],
                (
                    '("Jane Doe" OR "unidentified female" OR "unidentified woman" OR "unknown female") '
                    "{jurisdiction} ({age_band} OR {sex} OR {date_window} OR {distinguishing_marks})"
                ),
                notes="Score as compatibility lead only; no auto-merge to named subject.",
            ),
            _qf(
                "doe-john",
                "John Doe notices",
                ["john_doe_notice", "unidentified_remains", "cold_case_unidentified"],
                (
                    '("John Doe" OR "unidentified male" OR "unidentified man" OR "unknown male") '
                    "{jurisdiction} ({age_band} OR {sex} OR {date_window} OR {distinguishing_marks})"
                ),
                notes="Score as compatibility lead only; no auto-merge to named subject.",
            ),
            _qf(
                "doe-namus",
                "Unidentified remains clearinghouses",
                ["unidentified_remains", "medical_examiner_case", "cold_case_unidentified"],
                (
                    '(unidentified OR "NamUs" OR "Doe") {jurisdiction} '
                    "({age_band} OR {estimated_year_of_death} OR {hair} OR {height_band})"
                ),
            ),
            _qf(
                "doe-archive-clips",
                "Archive Doe / unidentified clippings",
                ["newspaper_archive_hit", "archive_crime_report", "cold_case_unidentified"],
                (
                    '("Jane Doe" OR "John Doe" OR unidentified) {jurisdiction} '
                    "({year_from}-{year_to}) (body OR remains OR discovered OR homicide)"
                ),
            ),
            _qf(
                "doe-id-news",
                "Later identification stories",
                ["news_identification", "public_tip_or_release"],
                (
                    '("identified as" OR "previously known as" OR "Jane Doe identified" OR '
                    '"John Doe identified") {jurisdiction} ({name} OR {aliases} OR {date_window})'
                ),
            ),
        ),
    ),
    "cold_missing": SearchMode(
        mode_id="cold_missing",
        title="Cold case — long-term missing",
        summary=(
            "Long-horizon missing notices plus archives, Doe options, "
            "and historical crime/publishing searches."
        ),
        event_classes=(
            "cold_case_missing",
            "missing_person_notice",
            "newspaper_archive_hit",
            "archive_missing_report",
            "historical_publication",
            "john_doe_notice",
            "jane_doe_notice",
            "unidentified_remains",
            "cold_case_unidentified",
            "archive_obituary",
            "vital_death_index",
        ),
        adapter_families=(
            "missing_registries",
            "newspaper_archives",
            "library_digital",
            "namus_unidentified",
            "me_doe_pages",
            "cold_case_public",
            "obituaries",
        ),
        cold_case=True,
        doe_match=True,
        archive=True,
        query_families=(
            _qf(
                "cold-missing-registry",
                "Long-term missing registries",
                ["cold_case_missing", "missing_person_notice"],
                (
                    '("{name}" OR {aliases}) (missing OR "cold case" OR "still missing" OR '
                    '"unsolved missing") {jurisdiction} ({year_from} OR {last_seen_year})'
                ),
            ),
            _qf(
                "cold-archive-name",
                "Name in historical newspapers",
                ["newspaper_archive_hit", "archive_missing_report", "historical_publication"],
                (
                    '("{name}" OR {aliases}) ({year_from}-{year_to}) (missing OR vanished OR '
                    '"last seen" OR disappeared) {jurisdiction_or_region}'
                ),
            ),
            _qf(
                "cold-cross-doe",
                "Cross-match Doe notices in window",
                ["jane_doe_notice", "john_doe_notice", "unidentified_remains"],
                (
                    '("Jane Doe" OR "John Doe" OR unidentified) {jurisdiction} '
                    "({age_band}) ({year_from}-{year_to})"
                ),
                notes="Enable when cold-case Doe option is selected.",
            ),
        ),
    ),
}


def list_search_modes() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for mode in SEARCH_MODES.values():
        out.append(
            {
                "mode_id": mode.mode_id,
                "title": mode.title,
                "summary": mode.summary,
                "cold_case": mode.cold_case,
                "doe_match": mode.doe_match,
                "archive": mode.archive,
                "event_classes": list(mode.event_classes),
                "adapter_families": list(mode.adapter_families),
                "query_family_count": len(mode.query_families),
            }
        )
    return out


def get_search_mode(mode_id: str) -> SearchMode:
    if mode_id not in SEARCH_MODES:
        raise KeyError(f"unknown search mode: {mode_id}")
    return SEARCH_MODES[mode_id]


def render_queries(
    mode_id: str,
    *,
    name: str = "{name}",
    aliases: str = "{aliases}",
    jurisdiction: str = "{jurisdiction}",
    jurisdiction_or_region: str | None = None,
    year_from: str = "{year_from}",
    year_to: str = "{year_to}",
    decade: str = "{decade}",
    age_band: str = "{age_band}",
    sex: str = "{sex}",
    date_window: str = "{date_window}",
    distinguishing_marks: str = "{distinguishing_marks}",
    estimated_year_of_death: str = "{estimated_year_of_death}",
    hair: str = "{hair}",
    height_band: str = "{height_band}",
    last_seen_year: str = "{last_seen_year}",
) -> dict[str, Any]:
    mode = get_search_mode(mode_id)
    tokens = {
        "{name}": name,
        "{aliases}": aliases,
        "{jurisdiction}": jurisdiction,
        "{jurisdiction_or_region}": jurisdiction_or_region or jurisdiction,
        "{year_from}": year_from,
        "{year_to}": year_to,
        "{decade}": decade,
        "{age_band}": age_band,
        "{sex}": sex,
        "{date_window}": date_window,
        "{distinguishing_marks}": distinguishing_marks,
        "{estimated_year_of_death}": estimated_year_of_death,
        "{hair}": hair,
        "{height_band}": height_band,
        "{last_seen_year}": last_seen_year,
    }

    def _sub(text: str) -> str:
        out = text
        for key, val in tokens.items():
            out = out.replace(key, val)
        return out

    families = []
    for qf in mode.query_families:
        families.append(
            {
                "family_id": qf.family_id,
                "title": qf.title,
                "event_classes": list(qf.event_classes),
                "template": qf.template,
                "rendered": _sub(qf.template),
                "notes": qf.notes,
            }
        )
    return {
        "mode_id": mode.mode_id,
        "title": mode.title,
        "summary": mode.summary,
        "cold_case": mode.cold_case,
        "doe_match": mode.doe_match,
        "archive": mode.archive,
        "event_classes": list(mode.event_classes),
        "queries": families,
        "boundary": (
            "Search plans only. Archive publication dates are not event dates. "
            "Doe hits are compatibility leads — never confirmed identity."
        ),
    }


def filter_pins_by_mode(pins: Iterable[Any], mode_id: str) -> list[Any]:
    """Keep pins whose event_class is in the mode, or all pins for mode 'active' all-view.

    For map filtering: modes other than a special 'all' filter to mode event classes.
    """
    if mode_id == "all":
        return list(pins)
    mode = get_search_mode(mode_id)
    allowed = set(mode.event_classes)
    return [p for p in pins if getattr(p, "event_class", None) in allowed]


def mode_payload(mode_id: str) -> dict[str, Any]:
    mode = get_search_mode(mode_id)
    return {
        "mode_id": mode.mode_id,
        "title": mode.title,
        "summary": mode.summary,
        "cold_case": mode.cold_case,
        "doe_match": mode.doe_match,
        "archive": mode.archive,
        "event_classes": list(mode.event_classes),
        "adapter_families": list(mode.adapter_families),
        "query_families": [asdict(q) | {"event_classes": list(q.event_classes)} for q in mode.query_families],
    }
