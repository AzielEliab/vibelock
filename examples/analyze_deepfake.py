"""Generate authentic vs attacked A/V cartoons and print scores.

No hardware. Author: Aziel Eliab.
"""

from __future__ import annotations

from vibelock import analyze
from vibelock.synth_media import authentic_av, authentic_image, deepfake_av, deepfake_image


def main() -> None:
    photo = analyze(image=authentic_image(96, 96, seed=2))
    fake_still = analyze(image=deepfake_image(96, 96, seed=8))
    good = authentic_av(duration_s=0.48, seed=5)
    bad = deepfake_av(duration_s=0.48, seed=11)
    av_ok = analyze(good.audio, good.sr, frames=good.frames, fps=good.fps)
    av_bad = analyze(bad.audio, bad.sr, frames=bad.frames, fps=bad.fps)
    print(f"authentic still  {photo.score:.3f}  {photo.verdict}  {photo.reason_codes}")
    print(f"deepfake still   {fake_still.score:.3f}  {fake_still.verdict}  {fake_still.reason_codes}")
    print(f"authentic A/V    {av_ok.score:.3f}  {av_ok.verdict}  {av_ok.reason_codes}")
    print(f"deepfake A/V     {av_bad.score:.3f}  {av_bad.verdict}  {av_bad.reason_codes}")


if __name__ == "__main__":
    main()
