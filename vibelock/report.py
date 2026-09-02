"""JSON reports: hashes, scores, and the courtroom limitation.

This is an audio authenticity advisory, not courtroom proof.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

from vibelock import __version__
from vibelock.scoring import AnalysisResult, format_human

LIMITATION = (
    "This is an audio authenticity advisory, not courtroom proof."
)
PLAIN_CONSISTENT = "This recording looks consistent with a real voice."
PLAIN_INCONSISTENT = (
    "This recording looks inconsistent — it might not match a real voice."
)
CONSISTENT_THRESHOLD = 0.5
PRODUCT = "vibelock"


def kid_plain(score: float) -> str:
    """One word a sixth-grader can use: consistent or inconsistent."""
    return "consistent" if float(score) >= CONSISTENT_THRESHOLD else "inconsistent"


def kid_sentence(score: float) -> str:
    return PLAIN_CONSISTENT if kid_plain(score) == "consistent" else PLAIN_INCONSISTENT


def build_report(
    result: AnalysisResult,
    *,
    sha256: str | None = None,
    sha256_vibration: str | None = None,
    filename: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Machine-readable export: scores, hashes, limitation. No waveform."""
    blob = result.to_dict()
    hashes: dict[str, str] = {}
    if sha256:
        hashes["sha256"] = str(sha256)
    if sha256_vibration:
        hashes["sha256_vibration"] = str(sha256_vibration)
    blob.update(
        {
            "product": PRODUCT,
            "version": __version__,
            "limitation": LIMITATION,
            "advisory": True,
            "courtroom_proof": False,
            "plain": kid_plain(result.score),
            "plain_sentence": kid_sentence(result.score),
            "hashes": hashes,
            "filename": filename,
            "telemetry": False,
        }
    )
    if extra:
        for key, value in extra.items():
            blob[key] = value
    return blob


def dumps_report(report: Mapping[str, Any]) -> str:
    return json.dumps(dict(report), indent=2) + "\n"


def format_report(report: Mapping[str, Any]) -> str:
    """Human text: kid-plain first, then the usual score block."""
    lines = [
        str(report.get("plain_sentence") or kid_sentence(float(report.get("score") or 0))),
        f"Limitation: {report.get('limitation') or LIMITATION}",
    ]
    resultish = report
    # format_human wants an AnalysisResult; rebuild a short header then checks.
    score = float(report.get("score") or 0.0)
    lines.append(f"VibeLock authenticity score: {score:.3f}")
    lines.append(f"Mode: {report.get('mode')}")
    codes = report.get("reason_codes") or []
    lines.append("Reason codes: " + (", ".join(codes) if codes else "(none)"))
    hashes = report.get("hashes") or {}
    if hashes.get("sha256"):
        lines.append(f"SHA-256: {hashes['sha256']}")
    if hashes.get("sha256_vibration"):
        lines.append(f"SHA-256 (vibration): {hashes['sha256_vibration']}")
    if report.get("filename"):
        lines.append(f"File: {report['filename']}")
    if report.get("verified"):
        lines.append("Verify: ok")
    sr = report.get("sample_rate")
    n = report.get("n_samples")
    if sr is not None and n is not None:
        lines.append(f"Sample rate: {sr} Hz, samples: {n}")
    notes = report.get("notes") or []
    for note in notes:
        lines.append(f"Note: {note}")
    checks = report.get("checks") or []
    if checks:
        lines.append("Checks:")
        for check in checks:
            flag = ""
            code = check.get("reason_code") if isinstance(check, dict) else None
            if code:
                flag = f" [{code}]"
            name = check.get("name") if isinstance(check, dict) else check
            cscore = check.get("score") if isinstance(check, dict) else 0.0
            lines.append(f"  - {name}: {float(cscore):.3f}{flag}")
    lines.append(LIMITATION)
    return "\n".join(lines)


def format_result(result: AnalysisResult, **kwargs: Any) -> str:
    return format_report(build_report(result, **kwargs))


# Keep a helper that still uses the original formatter when callers want it.
def legacy_human(result: AnalysisResult) -> str:
    return format_human(result)
