"""T19 classification calibration: run classifier/predictions on dev set and record ECE/curve/thresholds."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.classify.calibration import (  # noqa: E402
    apply_temperature,
    expected_calibration_error,
    fit_temperature,
    reliability_curve,
    select_operating_threshold,
    threshold_sweep,
)
from src.classify.classifier import DEFAULT_INTENTS, DEFAULT_URGENCIES, TicketClassifier  # noqa: E402
from src.config import get_config  # noqa: E402


def _mock_prediction(labels: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    """Label-informed mock predictions for calibration pipeline verification (documented)."""
    true_intent = labels.get("intent") or "unknown_intent"
    true_urgency = labels.get("urgency") or "unknown_urgency"
    intents = [i for i in DEFAULT_INTENTS if i != "unknown_intent"]
    urgencies = [u for u in DEFAULT_URGENCIES if u != "unknown_urgency"]

    # simulate correctness/confidence distribution
    p_intent_correct = 0.82
    p_urgency_correct = 0.90
    intent_correct = rng.random() < p_intent_correct
    urgency_correct = rng.random() < p_urgency_correct
    pred_intent = true_intent if intent_correct else rng.choice([i for i in intents if i != true_intent] or intents)
    pred_urgency = true_urgency if urgency_correct else rng.choice([u for u in urgencies if u != true_urgency] or urgencies)

    # confidence correlated imperfectly with correctness (so calibration is meaningful)
    if intent_correct and urgency_correct:
        base = rng.uniform(0.75, 0.99)
    elif intent_correct or urgency_correct:
        base = rng.uniform(0.45, 0.85)
    else:
        base = rng.uniform(0.15, 0.65)
    intent_conf = float(np.clip(base + rng.uniform(-0.08, 0.08), 0.0, 1.0))
    urgency_conf = float(np.clip(base + rng.uniform(-0.10, 0.10), 0.0, 1.0))
    overall = float(np.clip((intent_conf + urgency_conf) / 2.0 + rng.uniform(-0.05, 0.05), 0.0, 1.0))
    alternatives = [
        {"intent": pred_intent, "urgency": pred_urgency, "score": overall, "reason": "primary"},
    ]
    if not intent_correct:
        alternatives.append({"intent": true_intent, "urgency": pred_urgency, "score": max(0.0, overall - 0.1), "reason": "alternative"})
    return {
        "intent": pred_intent,
        "urgency": pred_urgency,
        "intent_confidence": intent_conf,
        "urgency_confidence": urgency_conf,
        "overall_confidence": overall,
        "alternatives": alternatives,
        "fallback_used": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="T19 calibration (ECE, reliability curve, threshold selection)")
    ap.add_argument("--mode", choices=["mock-labels", "real"], default="mock-labels")
    ap.add_argument("--limit", type=int, default=0, help="Limit number of dev tickets (0 = all)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output", default="docs/workbooks/t19_calibration_report.md")
    args = ap.parse_args()

    config = get_config()
    dev_path = config.paths.data_dir / "development_tickets.json"
    tickets = json.loads(dev_path.read_text(encoding="utf-8"))
    if args.limit and args.limit > 0:
        tickets = tickets[: args.limit]

    rng = random.Random(args.seed)
    classifier = TicketClassifier() if args.mode == "real" else None

    rows: List[Dict[str, Any]] = []
    for t in tickets:
        labels = t.get("labels") or {}
        true_intent = labels.get("intent")
        true_urgency = labels.get("urgency")
        if args.mode == "mock-labels":
            pred = _mock_prediction(labels, rng)
        else:
            # real mode (network/provider dependent)
            ticket_input = {
                "ticket_id": t.get("ticket_id"),
                "channel": t.get("channel"),
                "subject": t.get("subject"),
                "body": t.get("body"),
            }
            cls = classifier.classify_ticket(ticket_input)  # type: ignore[union-attr]
            pred = {
                "intent": cls.intent,
                "urgency": cls.urgency,
                "intent_confidence": cls.intent_confidence,
                "urgency_confidence": cls.urgency_confidence,
                "overall_confidence": cls.overall_confidence,
                "fallback_used": cls.fallback_used,
                "classifier_status": "fallback" if cls.fallback_used else "ok",
            }

        joint_correct = int(pred.get("intent") == true_intent and pred.get("urgency") == true_urgency)
        intent_correct = int(pred.get("intent") == true_intent)
        urgency_correct = int(pred.get("urgency") == true_urgency)
        rows.append(
            {
                "ticket_id": t.get("ticket_id"),
                "true_intent": true_intent,
                "true_urgency": true_urgency,
                "pred_intent": pred.get("intent"),
                "pred_urgency": pred.get("urgency"),
                "overall_confidence": float(pred.get("overall_confidence", 0.0)),
                "intent_confidence": float(pred.get("intent_confidence", 0.0)),
                "urgency_confidence": float(pred.get("urgency_confidence", 0.0)),
                "joint_correct": joint_correct,
                "intent_correct": intent_correct,
                "urgency_correct": urgency_correct,
                "fallback_used": bool(pred.get("fallback_used", False)),
            }
        )

    conf = [r["overall_confidence"] for r in rows]
    y = [r["joint_correct"] for r in rows]
    ece_raw = expected_calibration_error(conf, y, n_bins=10)
    temp = fit_temperature(conf, y)
    conf_cal = apply_temperature(conf, temp).tolist()
    ece_cal = expected_calibration_error(conf_cal, y, n_bins=10)
    bins_raw = [b.__dict__ for b in reliability_curve(conf, y, n_bins=10)]
    bins_cal = [b.__dict__ for b in reliability_curve(conf_cal, y, n_bins=10)]
    thresholds = [round(x, 2) for x in np.linspace(0.3, 0.95, 14).tolist()]
    sweep = threshold_sweep(conf_cal, y, thresholds)
    selected_threshold = select_operating_threshold(sweep, min_accuracy=0.80)

    report = {
        "mode": args.mode,
        "n_tickets": len(rows),
        "seed": args.seed,
        "method": "ECE + reliability bins (10). Temperature scaling fit by NLL grid-search on overall confidence; operating threshold selected by sweep on calibrated confidence (target >=0.80 accuracy on selected, max coverage).",
        "note": "mock-labels mode generates label-informed pseudo-predictions for calibration-pipeline/tooling verification (not real model calibration). Run with --mode real on dev set for true calibration.",
        "ece_raw_joint": ece_raw,
        "temperature": temp,
        "ece_calibrated_joint": ece_cal,
        "reliability_bins_raw": bins_raw,
        "reliability_bins_calibrated": bins_cal,
        "threshold_sweep_calibrated": sweep,
        "selected_operating_threshold_overall_confidence": selected_threshold,
        "accuracy_overall": float(np.mean(y)) if y else 0.0,
        "intent_accuracy": float(np.mean([r["intent_correct"] for r in rows])) if rows else 0.0,
        "urgency_accuracy": float(np.mean([r["urgency_correct"] for r in rows])) if rows else 0.0,
    }

    out_path = PROJECT_ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("# T19 Classification Calibration Report")
    lines.append("")
    lines.append(f"- Mode: `{args.mode}` | Tickets: **{len(rows)}** | Seed: `{args.seed}`")
    lines.append(f"- Method: {report['method']}")
    lines.append(f"- Note: {report['note']}")
    lines.append("")
    lines.append("## Calibration metrics (joint intent+urgency correctness vs overall confidence)")
    lines.append(f"- ECE (raw): **{ece_raw:.4f}**")
    lines.append(f"- Temperature (fitted): **{temp:.4f}**")
    lines.append(f"- ECE (calibrated): **{ece_cal:.4f}**")
    lines.append(f"- Accuracy (joint/intent/urgency): **{report['accuracy_overall']:.4f} / {report['intent_accuracy']:.4f} / {report['urgency_accuracy']:.4f}**")
    lines.append("")
    lines.append("## Operating threshold (calibrated overall confidence)")
    lines.append(f"- Selected threshold: **{selected_threshold:.2f}** (sweep on calibrated confidence; target >= 0.80 accuracy on selected, maximize coverage)")
    lines.append("")
    lines.append("### Threshold sweep (calibrated)")
    lines.append("| threshold | selected | coverage | accuracy_on_selected |")
    lines.append("|---:|---:|---:|---:|")
    for r in sweep:
        lines.append(f"| {r['threshold']:.2f} | {r['selected']} | {r['coverage']:.3f} | {r['accuracy_on_selected']:.3f} |")
    lines.append("")
    lines.append("### Reliability curve bins (raw)")
    lines.append("| bin | count | avg_conf | accuracy |")
    lines.append("|---|---:|---:|---:|")
    for b in bins_raw:
        lines.append(f"| [{b['bin_lower']:.1f},{b['bin_upper']:.1f}] | {b['count']} | {b['avg_confidence']:.3f} | {b['accuracy']:.3f} |")
    lines.append("")
    lines.append("### Reliability curve bins (calibrated)")
    lines.append("| bin | count | avg_conf | accuracy |")
    lines.append("|---|---:|---:|---:|")
    for b in bins_cal:
        lines.append(f"| [{b['bin_lower']:.1f},{b['bin_upper']:.1f}] | {b['count']} | {b['avg_confidence']:.3f} | {b['accuracy']:.3f} |")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(report, ensure_ascii=False, indent=2))
    lines.append("```")
    out_path.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "output": str(out_path),
        "n_tickets": len(rows),
        "mode": args.mode,
        "ece_raw_joint": ece_raw,
        "temperature": temp,
        "ece_calibrated_joint": ece_cal,
        "selected_operating_threshold_overall_confidence": selected_threshold,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
