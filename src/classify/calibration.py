"""Confidence calibration and threshold selection utilities (T19)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np


def _clip_prob(p: float, eps: float = 1e-6) -> float:
    return float(min(1.0 - eps, max(eps, p)))


def _logit(p: float) -> float:
    p = _clip_prob(p)
    return math.log(p / (1.0 - p))


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def apply_temperature(confidences: Sequence[float], temperature: float) -> np.ndarray:
    t = max(1e-3, float(temperature))
    out = np.array([_sigmoid(_logit(float(c)) / t) for c in confidences], dtype=float)
    return out


def fit_temperature(confidences: Sequence[float], correct: Sequence[int]) -> float:
    """Fit scalar temperature by grid-search minimizing NLL (documented/simple method)."""
    conf = np.array([_clip_prob(float(c)) for c in confidences], dtype=float)
    y = np.array([int(v) for v in correct], dtype=float)
    if len(conf) == 0:
        return 1.0
    best_t = 1.0
    best_nll = float("inf")
    # coarse-to-fine search
    for grid in (np.linspace(0.5, 3.0, 51), np.linspace(max(0.05, best_t - 0.25), best_t + 0.25, 51)):
        for t in grid:
            p = apply_temperature(conf, float(t))
            p = np.clip(p, 1e-6, 1 - 1e-6)
            nll = -float(np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
            if nll < best_nll:
                best_nll = nll
                best_t = float(t)
    # final fine pass around best_t
    for t in np.linspace(max(0.05, best_t - 0.1), best_t + 0.1, 41):
        p = apply_temperature(conf, float(t))
        p = np.clip(p, 1e-6, 1 - 1e-6)
        nll = -float(np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
        if nll < best_nll:
            best_nll = nll
            best_t = float(t)
    return float(best_t)


@dataclass
class ReliabilityBin:
    bin_lower: float
    bin_upper: float
    count: int
    avg_confidence: float
    accuracy: float


def reliability_curve(confidences: Sequence[float], correct: Sequence[int], n_bins: int = 10) -> List[ReliabilityBin]:
    conf = np.array([float(c) for c in confidences], dtype=float)
    y = np.array([int(v) for v in correct], dtype=int)
    bins: List[ReliabilityBin] = []
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    for i in range(n_bins):
        lo, hi = float(edges[i]), float(edges[i + 1])
        if i == n_bins - 1:
            mask = (conf >= lo) & (conf <= hi)
        else:
            mask = (conf >= lo) & (conf < hi)
        count = int(mask.sum())
        if count == 0:
            bins.append(ReliabilityBin(lo, hi, 0, 0.0, 0.0))
        else:
            bins.append(
                ReliabilityBin(
                    lo,
                    hi,
                    count,
                    float(conf[mask].mean()),
                    float(y[mask].mean()),
                )
            )
    return bins


def expected_calibration_error(confidences: Sequence[float], correct: Sequence[int], n_bins: int = 10) -> float:
    conf = np.array([float(c) for c in confidences], dtype=float)
    bins = reliability_curve(conf, correct, n_bins=n_bins)
    n = max(1, len(conf))
    ece = 0.0
    for b in bins:
        if b.count == 0:
            continue
        ece += (b.count / n) * abs(b.accuracy - b.avg_confidence)
    return float(ece)


def threshold_sweep(
    confidences: Sequence[float],
    correct: Sequence[int],
    thresholds: Sequence[float],
) -> List[Dict[str, float]]:
    conf = np.array([float(c) for c in confidences], dtype=float)
    y = np.array([int(v) for v in correct], dtype=int)
    rows = []
    total = len(conf)
    for t in thresholds:
        selected = conf >= float(t)
        n_sel = int(selected.sum())
        coverage = n_sel / total if total else 0.0
        accuracy = float(y[selected].mean()) if n_sel else 0.0
        rows.append(
            {
                "threshold": float(t),
                "selected": n_sel,
                "coverage": coverage,
                "accuracy_on_selected": accuracy,
            }
        )
    return rows


def select_operating_threshold(sweep_rows: Sequence[Dict[str, float]], min_accuracy: float = 0.8) -> float:
    """Pick highest-coverage threshold meeting min_accuracy; fallback to max accuracy."""
    eligible = [r for r in sweep_rows if r["accuracy_on_selected"] >= min_accuracy and r["selected"] > 0]
    if eligible:
        best = max(eligible, key=lambda r: (r["coverage"], r["accuracy_on_selected"], r["threshold"]))
        return float(best["threshold"])
    nonempty = [r for r in sweep_rows if r["selected"] > 0]
    if not nonempty:
        return 0.85
    best = max(nonempty, key=lambda r: (r["accuracy_on_selected"], r["coverage"]))
    return float(best["threshold"])
