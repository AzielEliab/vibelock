"""Channel citation on the existing analyze() path."""

from __future__ import annotations

from vibelock.scoring import analyze
from vibelock.synth_media import authentic_image


def test_image_only_channels() -> None:
    result = analyze(image=authentic_image(48, 48, seed=1))
    by_name = {c.name: c for c in result.channels}
    assert set(by_name) == {"physics", "linguistics", "vibration", "related"}
    assert by_name["physics"].status == "not_applicable"
    assert by_name["linguistics"].status == "not_applicable"
    assert by_name["vibration"].status == "insufficient"
    assert by_name["related"].status == "fired"
    assert by_name["related"].evidence == "heuristic"
    assert result.to_dict()["signals"] == ["spatial"]


def test_dual_channel_vibration_fires(authentic_pair) -> None:
    result = analyze(authentic_pair.audio, authentic_pair.sr, vibration=authentic_pair.vibration)
    vib = next(c for c in result.channels if c.name == "vibration")
    assert vib.status == "fired"
    assert vib.evidence == "measurement"
    assert "coherence" in vib.checks
    assert "synthetic" in vib.note
