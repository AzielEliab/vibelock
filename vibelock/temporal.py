"""Temporal video detectors: flicker, flow, identity, interpolation.

Per-frame generators (many face-swap and talking-head stacks) do not
share a single optical exposure. They flicker, warp identity without
motion, and leave interpolation ghosts. These checks stay in numpy.
"""

from __future__ import annotations

import numpy as np

from vibelock.media import frames_to_rgb01, to_gray01
from vibelock.scoring import (
    IDENTITY_FLICKER,
    INTERP_ARTIFACT,
    LIGHTING_INCONSISTENT,
    MOTION_INCONSISTENT,
    TEMPORAL_FLICKER,
    CheckResult,
    clip01,
    logistic_score,
)
from vibelock.vision import _gaussian, _sobel_mag, analyze_image


def _grays(frames: np.ndarray) -> np.ndarray:
    stack = frames_to_rgb01(frames)
    return np.stack([to_gray01(f) for f in stack], axis=0)


def _resize_gray(gray: np.ndarray, h: int, w: int) -> np.ndarray:
    """Nearest-neighbor resize — used only to bound flow cost."""
    ys = (np.linspace(0, gray.shape[0] - 1, h)).astype(np.int64)
    xs = (np.linspace(0, gray.shape[1] - 1, w)).astype(np.int64)
    return gray[ys][:, xs]


def block_flow(prev: np.ndarray, curr: np.ndarray, block: int = 8, search: int = 3) -> np.ndarray:
    """Integer block-matching flow. Returns (n_blocks, 2) of (dy, dx)."""
    a = np.asarray(prev, dtype=np.float64)
    b = np.asarray(curr, dtype=np.float64)
    h, w = a.shape
    # Downscale large frames so tests stay cheap.
    target = 48
    if max(h, w) > target:
        scale = target / float(max(h, w))
        a = _resize_gray(a, max(16, int(h * scale)), max(16, int(w * scale)))
        b = _resize_gray(b, a.shape[0], a.shape[1])
        h, w = a.shape
    flows: list[tuple[float, float]] = []
    for y in range(0, h - block + 1, block):
        for x in range(0, w - block + 1, block):
            patch = a[y : y + block, x : x + block]
            best = 1e18
            by = bx = 0
            for dy in range(-search, search + 1):
                yy = y + dy
                if yy < 0 or yy + block > h:
                    continue
                for dx in range(-search, search + 1):
                    xx = x + dx
                    if xx < 0 or xx + block > w:
                        continue
                    diff = patch - b[yy : yy + block, xx : xx + block]
                    sad = float(np.sum(diff * diff))
                    if sad < best:
                        best = sad
                        by, bx = dy, dx
            flows.append((float(by), float(bx)))
    if not flows:
        return np.zeros((1, 2), dtype=np.float64)
    return np.asarray(flows, dtype=np.float64)


def motion_energy(frames: np.ndarray) -> np.ndarray:
    """Per-frame-pair mean absolute difference (a cheap mouth-motion proxy)."""
    g = _grays(frames)
    if g.shape[0] < 2:
        return np.zeros(1, dtype=np.float64)
    d = np.abs(np.diff(g, axis=0))
    return np.mean(d.reshape(d.shape[0], -1), axis=1)


def check_flicker(frames: np.ndarray) -> CheckResult:
    g = _grays(frames)
    if g.shape[0] < 3:
        return CheckResult("flicker", 0.55, None, {}, "Need at least 3 frames.")
    means = g.mean(axis=(1, 2))
    stds = g.std(axis=(1, 2))
    # Detrend: smooth camera / talking-head motion is a slow mean drift.
    kern = np.ones(3) / 3.0
    if means.size >= 3:
        pad = np.pad(means, 1, mode="edge")
        trend = np.convolve(pad, kern, mode="valid")[: means.size]
        resid = means - trend
        dmean = float(np.max(np.abs(resid)))
    else:
        dmean = float(np.max(np.abs(np.diff(means))))
    dstd = float(np.max(np.abs(np.diff(stds))))
    rel = dmean / (float(np.std(means)) + 1e-6)
    score = clip01(min(logistic_score(dmean, good=0.008, bad=0.07), logistic_score(dstd, good=0.012, bad=0.08)))
    code = TEMPORAL_FLICKER if (dmean > 0.045 or dstd > 0.055) else None
    if code:
        score = min(score, 0.24)
    return CheckResult(
        name="flicker",
        score=score,
        reason_code=code,
        metrics={"max_dmean": dmean, "max_dstd": dstd, "rel_dmean": float(rel)},
        note="Frame-to-frame mean/std jumps (per-frame generator flicker).",
    )


def check_motion(frames: np.ndarray) -> CheckResult:
    g = _grays(frames)
    if g.shape[0] < 3:
        return CheckResult("motion", 0.55, None, {}, "Need at least 3 frames.")
    flows = [block_flow(g[i], g[i + 1]) for i in range(g.shape[0] - 1)]
    mags = [float(np.mean(np.sqrt(f[:, 0] ** 2 + f[:, 1] ** 2))) for f in flows]
    # Acceleration of the mean flow — natural motion is smooth.
    acc = float(np.max(np.abs(np.diff(mags)))) if len(mags) > 1 else 0.0
    last = flows[-1]
    if last.shape[0] > 2:
        rough = float(np.mean(np.std(last, axis=0)))
    else:
        rough = 0.0
    # A single translating object raises acc; only flag chaotic fields.
    score = clip01(logistic_score(rough, good=0.45, bad=2.4))
    code = MOTION_INCONSISTENT if rough > 1.75 else None
    if code:
        score = min(score, 0.28)
    return CheckResult(
        name="motion",
        score=score,
        reason_code=code,
        metrics={"flow_acc": acc, "flow_rough": rough, "mean_flow": float(np.mean(mags))},
        note="Block-matching flow acceleration and spatial roughness.",
    )


def check_identity(frames: np.ndarray) -> CheckResult:
    """Appearance changes that are not explained by motion energy."""
    g = _grays(frames)
    if g.shape[0] < 3:
        return CheckResult("identity", 0.55, None, {}, "Need at least 3 frames.")
    # Center crop — talking-head / portrait assumption.
    h, w = g.shape[1], g.shape[2]
    cy0, cy1 = h // 4, 3 * h // 4
    cx0, cx1 = w // 4, 3 * w // 4
    centers = g[:, cy0:cy1, cx0:cx1]
    # Histogram L1 between consecutive centers.
    bins = 16
    hist_l1: list[float] = []
    for i in range(centers.shape[0] - 1):
        ha, _ = np.histogram(centers[i], bins=bins, range=(0.0, 1.0), density=True)
        hb, _ = np.histogram(centers[i + 1], bins=bins, range=(0.0, 1.0), density=True)
        hist_l1.append(float(np.mean(np.abs(ha - hb))))
    energy = motion_energy(frames)
    # Identity flicker: large hist jump on a *truly still* pair.
    still = energy < 0.012
    still = still[: len(hist_l1)]
    if np.any(still):
        still_jump = float(np.max(np.asarray(hist_l1)[still]))
    else:
        still_jump = 0.0
    max_jump = float(np.max(hist_l1))
    score = clip01(logistic_score(still_jump if still_jump else 0.05, good=0.08, bad=0.55))
    code = IDENTITY_FLICKER if still_jump > 0.36 else None
    if code:
        score = min(score, 0.26)
    return CheckResult(
        name="identity",
        score=score,
        reason_code=code,
        metrics={"still_hist_l1": still_jump, "max_hist_l1": max_jump},
        note="Center-crop histogram jump on low-motion pairs (identity flicker).",
    )


def check_interp(frames: np.ndarray) -> CheckResult:
    """Ghosting: odd frames should not be a blend of neighbors (frame interp)."""
    g = _grays(frames)
    if g.shape[0] < 5:
        return CheckResult("interp", 0.60, None, {"n_frames": float(g.shape[0])}, "Need 5+ frames.")
    errs: list[float] = []
    for i in range(1, g.shape[0] - 1, 2):
        pred = 0.5 * (g[i - 1] + g[i + 1])
        residual = np.abs(g[i] - pred)
        # True in-between motion has structured residual; a blend is tiny.
        errs.append(float(np.mean(residual)))
    mean_err = float(np.mean(errs)) if errs else 0.05
    # Very small residual on textured clips → interpolated.
    tex = float(np.mean(np.abs(g - _gaussian(g.mean(axis=0), 1.0))))
    rel = mean_err / (tex + 1e-6)
    score = clip01(logistic_score(rel, good=0.55, bad=0.08))
    # Only flag when the clip has texture but mid-frames are blends.
    code = INTERP_ARTIFACT if (rel < 0.16 and tex > 0.02) else None
    if code:
        score = min(score, 0.30)
    return CheckResult(
        name="interp",
        score=score,
        reason_code=code,
        metrics={"mid_residual": mean_err, "rel_residual": float(rel), "texture": tex},
        note="Odd-frame residual vs linear blend of neighbors.",
    )


def check_lighting_drift(frames: np.ndarray) -> CheckResult:
    g = _grays(frames)
    if g.shape[0] < 3:
        return CheckResult("lighting", 0.55, None, {}, "Need at least 3 frames.")
    # Background shade: ignore high-gradient (moving) pixels.
    jumps = []
    for f in g:
        mag = _sobel_mag(f)
        bg = f[mag < float(np.percentile(mag, 60))]
        jumps.append(float(np.mean(bg)) if bg.size else float(np.mean(f)))
    shade = np.asarray(jumps, dtype=np.float64)
    jump = float(np.max(np.abs(np.diff(shade))))
    score = clip01(logistic_score(jump, good=0.012, bad=0.09))
    code = LIGHTING_INCONSISTENT if jump > 0.065 else None
    if code:
        score = min(score, 0.30)
    return CheckResult(
        name="lighting",
        score=score,
        reason_code=code,
        metrics={"shade_jump": jump},
        note="Global shade jump across frames (one-light physics over time).",
    )


def analyze_video(frames: np.ndarray, *, include_spatial: bool = True) -> list[CheckResult]:
    """Temporal battery, plus spatial checks on a mid frame when asked."""
    stack = frames_to_rgb01(frames)
    checks = [
        check_flicker(stack),
        check_motion(stack),
        check_identity(stack),
        check_interp(stack),
        check_lighting_drift(stack),
    ]
    if include_spatial and stack.shape[0] > 0:
        mid = stack[stack.shape[0] // 2]
        checks.extend(analyze_image(mid))
    return checks
