# VibeLock

**Physical-consistency evaluation of speech audio**

Aziel Eliab  
July 2026  
License: Apache-2.0

> Sound can be forged. Physics is harder to fake.

## Abstract

VibeLock evaluates whether audio is physically consistent with human vocal
vibration and biomechanical resonance. It is not a speaker-identification
system, not a watermark detector, and not a transcript pipeline. It asks a
narrower question: does this signal behave like air radiation that was
produced by a vibrating vocal tract, optionally corroborated by a
body-coupled sensor?

Two modes are defined.

1. **Dual-channel.** Air audio plus body-coupled vibration (jaw
   accelerometer, contact microphone, or IMU). The two streams are
   synchronized, drift-corrected, and compared in time, frequency, and
   phase.
2. **Audio-only forensic.** When vibration is absent, VibeLock still
   inspects spectral, phase, formant, resonance, and temporal structure.
   This mode is a *risk assessment*, not a proof of liveness.

The output of either mode is a probabilistic authenticity score in
\([0, 1]\) and a list of machine-readable reason codes.

This document is the specification implemented by the `vibelock` Python
package. It does not invent evaluation numbers, published ROC points, or
citations to studies that were not performed.

## 1. Motivation

Airborne speech can be synthesized, vocoded, spliced, and replayed.
Those operations are getting cheaper. What they still struggle to
reproduce, jointly, is the *physical coupling* between tissue vibration
and the sound that leaves the lips.

A jaw accelerometer, a throat contact mic, or a cheap IMU sitting on
the mandible sees a band-limited version of the same glottal events that
drive the vocal tract. That mapping is a transfer function with
constraints:

- energy in overlapping bands should cohere;
- the vibration-to-air map should look like a short acoustic tube, not
  like an independent renderer;
- delays are causal and small (vocal-tract group delay, not a network
  jitter buffer);
- resonances die quickly, because the tract is small.

Forged audio that was never in a body does not automatically satisfy
those constraints. Dual-channel VibeLock is built to say so, with
reasons.

When a second channel is not available, the same physics still leaves
fingerprints in the air signal — formant motion, phase continuity,
offset decay, splice edges, vocoder hop buzz. Audio-only mode reports
those fingerprints as risk, not as a verdict of “this is a real human.”

## 2. Scope and non-goals

**In scope**

- Local, CPU-only DSP (numpy / scipy).
- Dual-channel coherence, transfer-function residual, latency/drift,
  decay.
- Audio-only forensic checks listed in §5.
- Interpretable reason codes.
- Synthetic physically-plausible pairs as a *bootstrap prior* for the
  vibration-to-air map.

**Out of scope**

- Speech-to-text.
- Speaker identity, biometrics, or enrollment.
- Retention of raw audio by default.
- A published human contact-mic corpus. The transfer-function baseline
  is synthetic. That is documented in the code (`vibelock.synth`) and
  here, on purpose.
- Claimed accuracy percentages, equal-error rates, or “beats model X”
  tables. None are provided because none were measured on a public
  human set for this release.

## 3. Dual-channel analysis

Let \(a[n]\) be the air microphone and \(v[n]\) the body-coupled
vibration, both sampled at rate \(f_s\). Signals are mixed to mono and
optionally resampled to a common rate.

### 3.1 Synchronization and drift

A GCC-PHAT delay estimate aligns \(a\) to \(v\). The plausible delay
window is a few milliseconds (vocal-tract group delay and filter phase),
not tens of milliseconds. Windowed GCC-PHAT tracks drift; unbounded
drift is a sensor or edit artifact.

Reason codes: `LATENCY_OUT_OF_BOUNDS`, `DRIFT_EXCESSIVE`.

### 3.2 Vibration–audio coherence

Magnitude-squared coherence \(C_{va}(f)\) is estimated with Welch’s
method. Authentic coupled speech produces *stable* coherence in the
bands where both sensors carry energy, roughly 80–2000 Hz (coupling
band) and more broadly 80–4000 Hz (speech band). Independent renderers,
replay onto a dummy, or a vibration track taken from a different
utterance do not.

Time-varying MSC (short overlapping windows) measures stability.
Unstable or low in-band coherence emits `COHERENCE_LOW` or
`COHERENCE_UNSTABLE`.

### 3.3 Transfer-function consistency

The vibration-to-air map is

\[
H(f) = \frac{P_{va}(f)}{P_{vv}(f)}.
\]

A bootstrap baseline of \(\log|H(f)|\) is learned from synthetic
physically-plausible pairs: a glottal-like pulse train, a cascade of
second-order formant resonators for the air channel, and a low-pass
bone/tissue coupler for the vibration channel. **This baseline is
synthetic. It is not a published human dataset.**

The observed log-magnitude, gain-normalized, is compared to the
bootstrap mean and to the nearest ensemble member. A large residual, or
a roughness that looks like an uncorrelated pair, emits
`TRANSFER_RESIDUAL_HIGH`.

### 3.4 Phase and latency constraints

Causality: air radiation of a glottal event does not precede the tissue
vibration of that event by a physiologically absurd margin. Bounded
drift: once globally aligned, per-window delays stay tight. Violations
are `LATENCY_OUT_OF_BOUNDS` or `DRIFT_EXCESSIVE`. Hilbert-based phase
tools used on the air channel are shared with §5.

### 3.5 Resonance decay profiles

Vocal-tract ringing is short. Formant bandwidths of tens to a few
hundred hertz imply time constants of a few milliseconds
(\(\tau \approx 1/(\pi B)\)). Digital reverb and synthetic ringing
leave long, sometimes non-exponential tails.

VibeLock fits exponential envelopes to the *utterance offset* (the fall
from the last high-energy region to silence) and reports
`DECAY_IMPLAUSIBLE` when the offset is long in the way a feedback delay
network is long, not in the way a 17 cm tube is long.

## 4. Audio-only forensic mode

When \(v[n]\) is missing or unusable, VibeLock still runs. The score is
a risk assessment. It is explicitly *not* a proof of liveness: a careful
forger can still fool an air-only test, and a perfectly real recording
can look odd after heavy capture-chain processing.

Checks:

- **Spectral smoothness.** Log-magnitude fine structure after a
  formant-scale envelope. Over-smoothed vocoder spectra and
  noise-like/metallic spectra both move away from natural harmonic
  speech (`SPECTRAL_UNNATURAL`).
- **Phase continuity.** Hilbert instantaneous phase and detrended
  instantaneous frequency. Dense irregular jumps (`PHASE_DISCONTINUITY`);
  overly-flat phase from zero-phase reconstructions (`PHASE_OVERFLAT`).
- **Formant stability.** LPC peak tracks, frame to frame. Natural
  speech moves; it does not teleport every 25 ms (`FORMANT_UNSTABLE`).
- **Resonance behavior.** Same offset-decay test as §3.5.
- **Temporal artifacts.** Coincident RMS and spectral-flux spikes that
  are not stop-gap onsets (`TEMPORAL_SPLICE`). Envelope modulation at
  vocoder hop rates (`VOCODER_BUZZ`).

## 5. Scoring

Each check returns a subscore in \([0, 1]\) and optionally a reason
code. Dual-channel weights emphasize coherence, transfer residual, and
latency; audio-only weights emphasize phase, formants, and splices.
Thresholds in the implementation are **engineering defaults** chosen so
that synthetic fixtures move the score in the documented direction.
They are not operating points from a labeled human trial.

Reason codes include:

| Code | Meaning |
|---|---|
| `COHERENCE_LOW` | In-band MSC too low for a coupled pair |
| `COHERENCE_UNSTABLE` | MSC varies too much over time |
| `TRANSFER_RESIDUAL_HIGH` | Vibration-to-air map off the synthetic prior |
| `LATENCY_OUT_OF_BOUNDS` | GCC-PHAT delay outside the causal window |
| `DRIFT_EXCESSIVE` | Windowed delay not stable |
| `DECAY_IMPLAUSIBLE` | Offset tail looks like reverb / ringing |
| `PHASE_DISCONTINUITY` | Irregular Hilbert phase jumps |
| `PHASE_OVERFLAT` | Instantaneous-frequency residual too small |
| `FORMANT_UNSTABLE` | LPC peaks jump unnaturally |
| `TEMPORAL_SPLICE` | Hard join in the middle of energy |
| `SPECTRAL_UNNATURAL` | Fine structure too smooth or too noisy |
| `VOCODER_BUZZ` | Envelope peak at a hop-like rate |
| `VIBRATION_UNUSABLE` | Second channel present but empty / too short |
| `FREQ_FINGERPRINT` | Axial / lattice peaks in the high-pass 2-D spectrum |
| `NOISE_INCONSISTENT` | Tile residual-std mismatch (PRNU-like) |
| `BLOCK_ARTIFACT` | 8×8 boundary energy vs interior |
| `CHROMA_INCONSISTENT` | Local gray-world illuminant drift / R–B edge split |
| `BLEND_BOUNDARY` | Hard seam plus cross-seam color jump |
| `LIGHTING_INCONSISTENT` | Shading roughness or frame-to-frame shade jump |
| `TEMPORAL_FLICKER` | Per-frame mean/std flicker |
| `MOTION_INCONSISTENT` | Block-flow acceleration / roughness |
| `IDENTITY_FLICKER` | Center histogram jump on a still pair |
| `INTERP_ARTIFACT` | Odd frames are blends of neighbors |
| `PITCH_JUMP` | Unnatural F0 octave / semitone hop |
| `PITCH_OVERFLAT` | Robotic F0 (near-zero CV) |
| `FORMANT_PITCH_DECOUPLE` | F1 residual after an F0 fit (optional) |
| `PHASE_SHIFT_UNNATURAL` | Phase-vocoder / STFT IF over-flat |
| `AV_SYNC_FAIL` | Audio envelope vs mouth-proxy motion |

The composite score is a weighted mean of applicable checks, clipped to
\([0, 1]\). Visual / A/V modes also emit a `verdict` of `deepfake`,
`consistent`, or `inconclusive`.

## 6. Spatial image physics (September 2026)

A camera integrates photons under one (or a few) illuminants through
one lens. Generator stills and spliced portraits typically fail at
least one of:

- **Frequency lattice.** 2× nearest/bilinear upsampling parks energy on
  the half-Nyquist axes. Measured on a high-pass residual FFT.
- **Noise residual.** Tile coefficient of variation of a high-pass
  residual, plus center-vs-surround std (face-swap denoise).
- **Block energy.** 8×8 boundary vs interior gradients.
- **Illuminant.** Local gray-world \((C_b, C_r)\) spread; R/B edge
  alignment (CFA / registration physics).
- **Seams.** Projected strong-edge columns/rows plus a color jump.
- **Shading.** Low-frequency second differences of a Gaussian shade
  field.

These are DSP checks. They invent no published ROC numbers.

## 7. Temporal video physics

Per-frame generators do not share an exposure. VibeLock measures
flicker of frame mean/std, integer block-matching flow acceleration,
center-crop histogram jumps on low-motion pairs, odd-frame residual
versus a linear blend (interpolation ghosts), and global shade drift.

## 8. Unnatural pitch and phase shifts

Autocorrelation F0 tracks flag octave hops and robotic flatness.
An STFT instantaneous-frequency variance test flags phase-vocoder
time-stretch (horizontally locked bins).

## 9. Talking-head A/V coupling

The air RMS envelope is resampled to the frame grid and compared to
center-region motion energy. Pearson correlation plus a GCC-PHAT delay
on those envelopes emit `AV_SYNC_FAIL` when the mouth-proxy does not
produce the waveform.

## 10. Privacy

- No speech-to-text.
- No identity, enrollment, speaker embedding, or face recognition.
- Raw media is not retained by default. The library returns a score,
  reason codes, and numeric check metrics. The CLI does not write the
  input waveform or pixels anywhere.
- Processing is local. Hosted `/v1` accepts features or limited PCM,
  not a live microphone.

## 11. What this release is

A complete, inspectable implementation of the algorithms above, with
synthetic tests that prove each check moves the score the right way, a
CLI (`analyze` / `detect`), a localhost UI, and a Cloudflare Worker
that counts downloads and ports the same heuristics in JavaScript.

Forks are welcome and always allowed.

Sound can be forged. Pixels can be forged. Physics is harder to fake.

---

Sound can be forged. Pixels can be forged. Physics is harder to fake.

Signed,

Aziel
September 2026
