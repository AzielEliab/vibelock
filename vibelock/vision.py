"""Spatial image detectors: physics of light plus alteration artifacts.

Deepfake stills (GAN faces, diffusion composites, spliced portraits)
leave traces that a camera photon count does not:

* periodic Fourier peaks from generator upsampling
* tile-to-tile noise residual mismatch (PRNU-like)
* 8×8 block-energy inconsistency (mixed JPEG / synthetic)
* local illuminant drift (gray-world chromaticity physics)
* hard blend seams
* implausible local sharpness vs. a single lens

These are DSP checks (numpy + scipy). They are a risk assessment, not
courtroom proof, and they invent no published ROC numbers.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage

from vibelock.media import to_gray01, to_rgb01
from vibelock.scoring import (
    BLEND_BOUNDARY,
    BLOCK_ARTIFACT,
    CHROMA_INCONSISTENT,
    FREQ_FINGERPRINT,
    LIGHTING_INCONSISTENT,
    NOISE_INCONSISTENT,
    CheckResult,
    clip01,
    logistic_score,
)


def _gaussian(gray: np.ndarray, sigma: float) -> np.ndarray:
    return ndimage.gaussian_filter(gray, sigma=sigma, mode="nearest")


def _sobel_mag(gray: np.ndarray) -> np.ndarray:
    gx = ndimage.sobel(gray, axis=1, mode="nearest")
    gy = ndimage.sobel(gray, axis=0, mode="nearest")
    return np.hypot(gx, gy)


def _tiles(arr: np.ndarray, size: int) -> list[np.ndarray]:
    h, w = arr.shape[:2]
    out: list[np.ndarray] = []
    for y in range(0, h - size + 1, size):
        for x in range(0, w - size + 1, size):
            out.append(arr[y : y + size, x : x + size])
    return out


def check_spatial_freq(image: np.ndarray) -> CheckResult:
    """Axial / grid peaks in the high-pass residual spectrum.

    Nearest/bilinear 2× generator upsampling parks energy on the
    Nyquist-half lattice. Natural 1/f scenes do not.
    """
    gray = to_gray01(image)
    residual = gray - _gaussian(gray, 1.15)
    residual = residual - float(np.mean(residual))
    nfft_h = max(32, int(1 << (gray.shape[0] - 1).bit_length()))
    nfft_w = max(32, int(1 << (gray.shape[1] - 1).bit_length()))
    win = np.outer(np.hanning(gray.shape[0]), np.hanning(gray.shape[1]))
    spec = np.abs(np.fft.fftshift(np.fft.fft2(residual * win, s=(nfft_h, nfft_w))))
    spec = spec / (float(np.median(spec)) + 1e-12)
    cy, cx = nfft_h // 2, nfft_w // 2
    # Mid-band rings (0.22–0.42 cycles/pixel) along axes — classic upsample.
    yy, xx = np.ogrid[:nfft_h, :nfft_w]
    fy = (yy - cy) / float(nfft_h)
    fx = (xx - cx) / float(nfft_w)
    rad = np.sqrt(fy * fy + fx * fx)
    mid = (rad > 0.20) & (rad < 0.46)
    axial = mid & ((np.abs(fy) < 0.035) | (np.abs(fx) < 0.035))
    band = spec[mid]
    axis = spec[axial] if np.any(axial) else band
    peak = float(np.percentile(axis, 99.5)) if axis.size else 1.0
    med = float(np.median(band) + 1e-12) if band.size else 1.0
    ratio = peak / med
    # Also a checkerboard cue: energy near (±0.25, ±0.25) vs nearby.
    def _box(fy0: float, fx0: float, hw: float = 0.03) -> float:
        m = (np.abs(fy - fy0) < hw) & (np.abs(fx - fx0) < hw)
        return float(np.mean(spec[m])) if np.any(m) else 0.0

    check_e = (
        _box(0.25, 0.0)
        + _box(-0.25, 0.0)
        + _box(0.0, 0.25)
        + _box(0.0, -0.25)
        + _box(0.25, 0.25)
        + _box(0.25, -0.25)
    ) / 6.0
    neigh = (
        _box(0.18, 0.12)
        + _box(0.12, 0.18)
        + _box(0.32, 0.12)
        + _box(0.12, 0.32)
    ) / 4.0
    lattice = check_e / (neigh + 1e-12)
    score = clip01(min(logistic_score(ratio, good=3.2, bad=14.0), logistic_score(lattice, good=1.15, bad=3.4)))
    code = FREQ_FINGERPRINT if (ratio > 8.5 or lattice > 2.2) else None
    if code:
        score = min(score, 0.28)
    return CheckResult(
        name="spatial_freq",
        score=score,
        reason_code=code,
        metrics={"spec_peak_ratio": ratio, "lattice_ratio": float(lattice), "check_e": float(check_e)},
        note="High-pass 2-D FFT lattice / axial peaks (generator upsampling).",
    )


def check_noise(image: np.ndarray) -> CheckResult:
    """Tile residual-std coefficient of variation (PRNU-like mismatch)."""
    gray = to_gray01(image)
    resid = gray - _gaussian(gray, 0.85)
    size = 8 if min(gray.shape) >= 32 else max(4, min(gray.shape) // 4)
    tiles = _tiles(resid, size)
    if len(tiles) < 4:
        return CheckResult("noise", 0.5, None, {}, "Too small to tile.")
    stds = np.array([float(np.std(t)) for t in tiles], dtype=np.float64)
    mean_std = float(np.mean(stds) + 1e-12)
    cv = float(np.std(stds) / mean_std)
    # Center vs surround: deepfake faces often denoise the portrait.
    h, w = resid.shape
    cy0, cy1 = h // 4, 3 * h // 4
    cx0, cx1 = w // 4, 3 * w // 4
    center = float(np.std(resid[cy0:cy1, cx0:cx1]) + 1e-12)
    # Surround = everything else via a mask.
    mask = np.ones_like(resid, dtype=bool)
    mask[cy0:cy1, cx0:cx1] = False
    surround = float(np.std(resid[mask]) + 1e-12)
    cs = max(center / surround, surround / center)
    score = clip01(min(logistic_score(cv, good=0.22, bad=0.85), logistic_score(cs, good=1.15, bad=3.2)))
    code = NOISE_INCONSISTENT if (cv > 0.62 or cs > 2.15) else None
    if code:
        score = min(score, 0.28)
    return CheckResult(
        name="noise",
        score=score,
        reason_code=code,
        metrics={"tile_std_cv": cv, "center_surround": float(cs), "mean_resid_std": mean_std},
        note="High-pass residual std across tiles and center vs surround.",
    )


def check_block(image: np.ndarray) -> CheckResult:
    """8×8 block-boundary energy vs interior (mixed compression / synth)."""
    gray = to_gray01(image)
    h, w = gray.shape
    if h < 16 or w < 16:
        return CheckResult("block", 0.55, None, {}, "Too small for 8×8 blocks.")
    dx = np.abs(np.diff(gray, axis=1))
    dy = np.abs(np.diff(gray, axis=0))
    # Boundaries at x = 8, 16, … (between pixels 7|8).
    xs = np.arange(7, w - 1, 8)
    ys = np.arange(7, h - 1, 8)
    bound = 0.0
    n_b = 0
    if xs.size:
        bound += float(np.mean(dx[:, xs]))
        n_b += 1
    if ys.size:
        bound += float(np.mean(dy[ys, :]))
        n_b += 1
    bound = bound / max(n_b, 1)
    # Interior: offsets 3, 4, 5 inside each block.
    ix = [i for i in range(w - 1) if (i % 8) in {2, 3, 4}]
    iy = [i for i in range(h - 1) if (i % 8) in {2, 3, 4}]
    interior = 0.0
    n_i = 0
    if ix:
        interior += float(np.mean(dx[:, ix]))
        n_i += 1
    if iy:
        interior += float(np.mean(dy[iy, :]))
        n_i += 1
    interior = interior / max(n_i, 1) + 1e-12
    ratio = bound / interior
    # Regional inconsistency of the same ratio (spliced JPEG + GAN).
    ratios: list[float] = []
    for y0 in range(0, h - 16, 16):
        for x0 in range(0, w - 16, 16):
            patch = gray[y0 : y0 + 16, x0 : x0 + 16]
            pdx = np.abs(np.diff(patch, axis=1))
            b = float(np.mean(pdx[:, [7]])) if pdx.shape[1] > 7 else 0.0
            inn = float(np.mean(pdx[:, [3, 4]])) + 1e-12
            ratios.append(b / inn)
    spread = float(np.std(ratios)) if len(ratios) > 1 else 0.0
    score = clip01(min(logistic_score(ratio, good=1.05, bad=1.85), logistic_score(spread, good=0.08, bad=0.55)))
    code = BLOCK_ARTIFACT if (ratio > 1.70 and spread > 0.22) or ratio > 2.05 else None
    if code:
        score = min(score, 0.32)
    return CheckResult(
        name="block",
        score=score,
        reason_code=code,
        metrics={"boundary_interior": float(ratio), "block_ratio_std": spread},
        note="8×8 boundary vs interior gradient energy.",
    )


def _ycbcr(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    y = 0.299 * r + 0.587 * g + 0.114 * b
    cb = -0.168736 * r - 0.331264 * g + 0.5 * b + 0.5
    cr = 0.5 * r - 0.418688 * g - 0.081312 * b + 0.5
    return y, cb, cr


def check_chroma(image: np.ndarray) -> CheckResult:
    """Local gray-world illuminant consistency (one-light physics)."""
    rgb = to_rgb01(image)
    _y, cb, cr = _ycbcr(rgb)
    size = 8 if min(rgb.shape[:2]) >= 32 else max(4, min(rgb.shape[:2]) // 4)
    tiles_cb = _tiles(cb, size)
    tiles_cr = _tiles(cr, size)
    if len(tiles_cb) < 4:
        return CheckResult("chroma", 0.5, None, {}, "Too small for chroma tiles.")
    means = np.array(
        [[float(np.mean(a)), float(np.mean(b))] for a, b in zip(tiles_cb, tiles_cr)],
        dtype=np.float64,
    )
    # Drop near-black tiles (undefined illuminant).
    y = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    y_tiles = _tiles(y, size)
    keep = np.array([float(np.mean(t)) > 0.08 for t in y_tiles])
    if np.count_nonzero(keep) >= 4:
        means = means[keep]
    spread = float(np.mean(np.var(means, axis=0)))
    # Channel misalignment: R vs B edge maps should match a camera CFA, not a shift.
    er = _sobel_mag(rgb[..., 0])
    eb = _sobel_mag(rgb[..., 2])
    er = er / (float(np.linalg.norm(er)) + 1e-12)
    eb = eb / (float(np.linalg.norm(eb)) + 1e-12)
    align = float(np.sum(er * eb))
    score = clip01(min(logistic_score(spread, good=0.0008, bad=0.012), logistic_score(align, good=0.85, bad=0.35)))
    code = CHROMA_INCONSISTENT if (spread > 0.0065 or align < 0.48) else None
    if code:
        score = min(score, 0.30)
    return CheckResult(
        name="chroma",
        score=score,
        reason_code=code,
        metrics={"illuminant_var": spread, "rb_edge_align": align},
        note="Local gray-world chromaticity and R/B edge alignment.",
    )


def check_blend(image: np.ndarray) -> CheckResult:
    """Hard seam / matte: a long high-gradient contour that is not texture."""
    gray = to_gray01(image)
    mag = _sobel_mag(gray)
    thr = float(np.percentile(mag, 92))
    edges = mag >= max(thr, 1e-6)
    # Vertical and horizontal projections of strong edges.
    col = edges.mean(axis=0)
    row = edges.mean(axis=1)
    seam = float(max(np.max(col) if col.size else 0.0, np.max(row) if row.size else 0.0))
    # Color jump across the strongest column.
    rgb = to_rgb01(image)
    if col.size:
        j = int(np.argmax(col))
        j = min(max(j, 1), rgb.shape[1] - 2)
        left = rgb[:, max(0, j - 3) : j].reshape(-1, 3)
        right = rgb[:, j + 1 : min(rgb.shape[1], j + 4)].reshape(-1, 3)
        color_jump = float(np.linalg.norm(left.mean(axis=0) - right.mean(axis=0)))
    else:
        color_jump = 0.0
    score = clip01(min(logistic_score(seam, good=0.18, bad=0.62), logistic_score(color_jump, good=0.04, bad=0.28)))
    code = BLEND_BOUNDARY if (seam > 0.36 and color_jump > 0.08) or seam > 0.62 or color_jump > 0.20 else None
    if code:
        score = min(score, 0.26)
    return CheckResult(
        name="blend",
        score=score,
        reason_code=code,
        metrics={"seam_frac": seam, "color_jump": color_jump},
        note="Projected strong-edge seam plus cross-seam color jump.",
    )


def check_lighting(image: np.ndarray) -> CheckResult:
    """Single-source shading physics: low-frequency lighting should be smooth."""
    gray = to_gray01(image)
    shade = _gaussian(gray, max(2.5, 0.06 * min(gray.shape)))
    # Second differences of the shade field — a point light / window is smooth.
    d2y = np.diff(shade, n=2, axis=0)
    d2x = np.diff(shade, n=2, axis=1)
    h2 = min(d2y.shape[0], d2x.shape[0])
    w2 = min(d2y.shape[1], d2x.shape[1])
    yy = d2y[:h2, :w2]
    xx = d2x[:h2, :w2]
    rough = float(np.mean(yy * yy + xx * xx))
    # Local mean jumps on a coarse grid.
    step = max(8, min(gray.shape) // 6)
    means = []
    for y in range(0, gray.shape[0] - step + 1, step):
        for x in range(0, gray.shape[1] - step + 1, step):
            means.append(float(np.mean(shade[y : y + step, x : x + step])))
    jumps = float(np.mean(np.abs(np.diff(means)))) if len(means) > 1 else 0.0
    score = clip01(min(logistic_score(rough, good=1.5e-6, bad=8e-5), logistic_score(jumps, good=0.04, bad=0.22)))
    code = LIGHTING_INCONSISTENT if (rough > 4.5e-5 or jumps > 0.16) else None
    if code:
        score = min(score, 0.32)
    return CheckResult(
        name="lighting",
        score=score,
        reason_code=code,
        metrics={"shade_rough": rough, "shade_jump": jumps},
        note="Low-frequency shading roughness (single-illuminant physics).",
    )


def analyze_image(image: np.ndarray) -> list[CheckResult]:
    """Run the spatial deepfake battery on one RGB still."""
    rgb = to_rgb01(image)
    return [
        check_spatial_freq(rgb),
        check_noise(rgb),
        check_block(rgb),
        check_chroma(rgb),
        check_blend(rgb),
        check_lighting(rgb),
    ]
