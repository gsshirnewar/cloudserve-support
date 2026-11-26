"""Local-only T26 diagnostics; does not call an external model provider."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.retrieve.retriever import RetrievalIndex


CONFIDENCE_THRESHOLDS = [round(x / 100, 2) for x in range(30, 100, 5)]
RETRIEVAL_THRESHOLDS = [round(x / 100, 2) for x in range(0, 100, 5)]


def _holdout(ticket_id: str) -> bool:
    digest = hashlib.sha256(ticket_id.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 5 == 0


def _expected_docs(ticket: Mapping[str, Any]) -> set[str]:
    labels = ticket.get("labels")
    values = labels.get("expected_doc_ids") if isinstance(labels, Mapping) else []
    if not isinstance(values, list):
        return set()
    return {str(value) for value in values if value}


def _score_retrieval_threshold(
    examples: Sequence[Mapping[str, Any]],
    threshold: float,
) -> Dict[str, Any]:
    evaluated = [row for row in examples if row["expected_docs"]]
    true_positive = false_positive = false_negative = 0
    queries_with_results = hit_queries = 0
    for row in evaluated:
        expected = set(row["expected_docs"])
        retrieved = {
            str(hit["doc_id"])
            for hit in row["hits"]
            if float(hit["score"]) >= threshold
        }
        queries_with_results += int(bool(retrieved))
        matching = expected & retrieved
        hit_queries += int(bool(matching))
        true_positive += len(matching)
        false_positive += len(retrieved - expected)
        false_negative += len(expected - retrieved)

    precision_denominator = true_positive + false_positive
    recall_denominator = true_positive + false_negative
    precision = true_positive / precision_denominator if precision_denominator else None
    recall = true_positive / recall_denominator if recall_denominator else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    count = len(evaluated)
    return {
        "threshold": threshold,
        "answerable_ticket_count": count,
        "query_coverage": queries_with_results / count if count else None,
        "ticket_hit_rate": hit_queries / count if count else None,
        "doc_precision": precision,
        "doc_recall": recall,
        "doc_f1": f1,
        "retrieved_unique_docs": precision_denominator,
        "expected_unique_docs": recall_denominator,
    }


def _confidence_sweep(
    tickets: Sequence[Mapping[str, Any]],
    records: Mapping[int, Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    rows = []
    for threshold in CONFIDENCE_THRESHOLDS:
        selected = 0
        wrong_route = 0
        for index, ticket in enumerate(tickets):
            result = records[index].get("result", {})
            classification = result.get("classification") or {}
            confidence = float(classification.get("overall_confidence") or 0.0)
            if classification.get("fallback_used") or confidence < threshold:
                continue
            selected += 1
            labels = ticket.get("labels") if isinstance(ticket.get("labels"), Mapping) else {}
            wrong_route += int(labels.get("expected_route") != "auto_respond")
        rows.append({
            "confidence_threshold": threshold,
            "auto_candidate_count": selected,
            "auto_candidate_coverage": selected / len(tickets) if tickets else None,
            "wrong_route_count": wrong_route,
            "wrong_route_rate": wrong_route / selected if selected else None,
        })
    return rows


def _svg_line_chart(
    path: Path,
    title: str,
    series: Sequence[tuple[str, Sequence[tuple[float, Optional[float]]], str]],
    *,
    empty_message: Optional[str] = None,
) -> None:
    width, height = 840, 480
    left, top, plot_width, plot_height = 80, 60, 700, 330
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2}" y="30" text-anchor="middle" font-family="sans-serif" font-size="18">{html.escape(title)}</text>',
    ]
    for tick in range(0, 11):
        y = top + plot_height * (1 - tick / 10)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left+plot_width}" y2="{y:.1f}" stroke="#dddddd"/>')
        parts.append(f'<text x="{left-12}" y="{y+4:.1f}" text-anchor="end" font-family="sans-serif" font-size="11">{tick/10:.1f}</text>')
    parts.extend([
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_height}" stroke="#333"/>',
        f'<line x1="{left}" y1="{top+plot_height}" x2="{left+plot_width}" y2="{top+plot_height}" stroke="#333"/>',
        f'<text x="{left+plot_width/2}" y="{height-18}" text-anchor="middle" font-family="sans-serif" font-size="12">Threshold</text>',
        f'<text x="20" y="{top+plot_height/2}" transform="rotate(-90 20 {top+plot_height/2})" text-anchor="middle" font-family="sans-serif" font-size="12">Rate</text>',
    ])
    if empty_message:
        parts.append(f'<text x="{left+plot_width/2}" y="{top+plot_height/2}" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#555">{html.escape(empty_message)}</text>')
    else:
        for series_index, (name, points, color) in enumerate(series):
            valid = [(x, y) for x, y in points if y is not None]
            if valid:
                polyline = " ".join(
                    f"{left + x * plot_width:.1f},{top + (1 - y) * plot_height:.1f}"
                    for x, y in valid
                )
                parts.append(f'<polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="2"/>')
            legend_x = left + series_index * 175
            parts.append(f'<line x1="{legend_x}" y1="{height-45}" x2="{legend_x+24}" y2="{height-45}" stroke="{color}" stroke-width="3"/>')
            parts.append(f'<text x="{legend_x+30}" y="{height-41}" font-family="sans-serif" font-size="11">{html.escape(name)}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def run_local_diagnostics(input_path: Path, run_dir: Path, output_dir: Path) -> Dict[str, Any]:
    tickets = json.loads(input_path.read_text(encoding="utf-8-sig"))
    if not isinstance(tickets, list):
        raise ValueError("T26 input must be a JSON array of development tickets.")
    records: Dict[int, Dict[str, Any]] = {}
    results_path = run_dir / "results.jsonl"
    for line in results_path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        index = record.get("input_index")
        if not isinstance(index, int) or index < 0 or index >= len(tickets):
            raise ValueError(f"Invalid result input_index: {index!r}")
        records[index] = record
    if len(records) != len(tickets) or sorted(records) != list(range(len(tickets))):
        raise ValueError(f"Expected {len(tickets)} indexed results; found {len(records)}.")

    fallback_count = 0
    intent_correct = urgency_correct = 0
    for index, ticket in enumerate(tickets):
        classification = (records[index].get("result") or {}).get("classification") or {}
        labels = ticket.get("labels") if isinstance(ticket.get("labels"), Mapping) else {}
        fallback_count += int(bool(classification.get("fallback_used")))
        intent_correct += int(classification.get("intent") == labels.get("intent"))
        urgency_correct += int(classification.get("urgency") == labels.get("urgency"))

    index = RetrievalIndex(relevance_threshold=0.0)
    index.ensure_ready(rebuild_if_missing=False)
    examples = []
    for ticket in tickets:
        query = " ".join((str(ticket.get("subject") or ""), str(ticket.get("body") or ""))).strip()
        hits = index.search(query, top_k=5, relevance_threshold=0.0)
        examples.append({
            "ticket_id": str(ticket.get("ticket_id") or ""),
            "expected_docs": sorted(_expected_docs(ticket)),
            "hits": [{"doc_id": hit.doc_id, "score": float(hit.score)} for hit in hits],
            "is_holdout": _holdout(str(ticket.get("ticket_id") or "")),
        })

    train = [row for row in examples if not row["is_holdout"]]
    holdout = [row for row in examples if row["is_holdout"]]
    retrieval_sweep = []
    for threshold in RETRIEVAL_THRESHOLDS:
        retrieval_sweep.append({
            "threshold": threshold,
            "train": _score_retrieval_threshold(train, threshold),
            "holdout": _score_retrieval_threshold(holdout, threshold),
        })

    candidate_rows = [
        row for row in retrieval_sweep
        if row["train"]["doc_f1"] is not None
    ]
    best_retrieval_candidate = max(
        candidate_rows,
        key=lambda row: (
            row["train"]["doc_f1"],
            row["train"]["doc_precision"] or 0.0,
            row["threshold"],
        ),
    ) if candidate_rows else None
    confidence_sweep = _confidence_sweep(tickets, records)

    output_dir.mkdir(parents=True, exist_ok=True)
    sweep_json = {
        "status": "incomplete_no_model_predictions",
        "data_scope": str(input_path),
        "tickets": len(tickets),
        "holdout_method": "ticket_id SHA-256 first-32-bit modulo 5; deterministic 80/20 split",
        "local_retrieval_backend": index.info().get("embedding_backend", index.info().get("backend")),
        "classification": {
            "fallback_count": fallback_count,
            "fallback_rate": fallback_count / len(tickets) if tickets else None,
            "intent_accuracy_including_fallback": intent_correct / len(tickets) if tickets else None,
            "urgency_accuracy_including_fallback": urgency_correct / len(tickets) if tickets else None,
            "valid_nonfallback_confidence_count": len(tickets) - fallback_count,
            "calibration_status": "unavailable: no valid non-fallback classifier predictions",
        },
        "confidence_threshold_sweep": confidence_sweep,
        "retrieval_threshold_sweep": retrieval_sweep,
        "best_retrieval_threshold_candidate_on_train": best_retrieval_candidate,
        "threshold_freeze": {
            "status": "not_frozen",
            "reason": "Classifier confidence calibration is unavailable in local-only fallback mode; retrieval index uses hash embeddings rather than the specified MiniLM model.",
            "current_config_retained": {
                "route_auto_min_confidence": 0.85,
                "route_assist_min_confidence": 0.60,
                "retrieval_relevance_threshold": 0.30,
            },
        },
        "privacy": {
            "external_provider_calls": 0,
            "ticket_content_sent_outside_machine": False,
        },
    }
    (output_dir / "threshold_sweep.json").write_text(
        json.dumps(sweep_json, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with (output_dir / "retrieval_threshold_sweep.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            "threshold", "train_coverage", "train_ticket_hit_rate", "train_doc_precision", "train_doc_recall", "train_doc_f1",
            "holdout_coverage", "holdout_ticket_hit_rate", "holdout_doc_precision", "holdout_doc_recall", "holdout_doc_f1",
        ])
        for row in retrieval_sweep:
            writer.writerow([
                row["threshold"],
                row["train"]["query_coverage"],
                row["train"]["ticket_hit_rate"],
                row["train"]["doc_precision"],
                row["train"]["doc_recall"],
                row["train"]["doc_f1"],
                row["holdout"]["query_coverage"],
                row["holdout"]["ticket_hit_rate"],
                row["holdout"]["doc_precision"],
                row["holdout"]["doc_recall"],
                row["holdout"]["doc_f1"],
            ])

    train_points = [
        (row["threshold"], row["train"]["doc_precision"])
        for row in retrieval_sweep
    ]
    holdout_points = [
        (row["threshold"], row["holdout"]["doc_precision"])
        for row in retrieval_sweep
    ]
    _svg_line_chart(
        output_dir / "retrieval_threshold_tradeoff.svg",
        "Local retrieval precision by relevance threshold",
        [
            ("Train document precision", train_points, "#2463a6"),
            ("Holdout document precision", holdout_points, "#d97706"),
        ],
    )
    _svg_line_chart(
        output_dir / "confidence_reliability.svg",
        "Classifier confidence reliability (unavailable)",
        [],
        empty_message="No non-fallback classifier predictions; reliability cannot be estimated.",
    )

    best_threshold = best_retrieval_candidate["threshold"] if best_retrieval_candidate else None
    report_lines = [
        "# T26 local-only diagnostic (incomplete)",
        "",
        "## Scope and privacy",
        "",
        f"- Development tickets evaluated: **{len(tickets)}**; no validation data was read.",
        "- External provider calls: **0**. Ticket contents remained local.",
        "- A deterministic 80/20 development split was used for the retrieval-threshold diagnostic.",
        "",
        "## Classifier and routing results",
        "",
        f"- Provider-disconnected classifier fallbacks: **{fallback_count}/{len(tickets)} ({(fallback_count / len(tickets) * 100) if tickets else 0:.1f}%)**.",
        f"- Intent accuracy including fallback predictions: **{(intent_correct / len(tickets)) if tickets else 0:.4f}**.",
        f"- Urgency accuracy including fallback predictions: **{(urgency_correct / len(tickets)) if tickets else 0:.4f}**.",
        "- These are outage/fallback outcomes, not a valid quality estimate of the configured LLM classifier.",
        "- No non-fallback confidence observations exist, so ECE, temperature fitting, confidence-vs-wrong-answer tradeoffs, and a route-confidence threshold cannot be estimated.",
        "",
        "## Local retrieval threshold sweep",
        "",
        f"- Retrieval backend: `{sweep_json['local_retrieval_backend']}`.",
        "- The plot and CSV show document-level precision/recall proxies against `expected_doc_ids`, separated by the deterministic train/holdout split.",
        f"- Best training-split candidate by document F1: **{best_threshold if best_threshold is not None else 'n/a'}**. This is diagnostic only and is not frozen because the active index uses hash fallback embeddings, not the specified MiniLM model.",
        "- See `retrieval_threshold_sweep.csv` and `retrieval_threshold_tradeoff.svg` for all thresholds.",
        "",
        "## Threshold decision",
        "",
        "**T26 is not complete and no thresholds are frozen.** Existing defaults (auto confidence 0.85, assist confidence 0.60, retrieval relevance 0.30) remain unchanged. Changing them from fallback-only predictions or hash-fallback retrieval would not be evidence-based.",
        "",
        "The route implementation was corrected before this diagnostic so `labels.answerable_from_docs` and `labels.must_not_auto_respond` no longer control production routing. The classifier real-mode calibration script was aligned with the current `Classification` schema.",
        "",
        "To complete T26 while keeping data local, configure a local inference runtime for the capstone-specified model and the required MiniLM retrieval dependencies, then rerun the dev-only calibration. The locally installed Qwen model was not substituted: a synthetic one-ticket smoke request exceeded the 120-second limit.",
        "",
        "The confidence reliability chart is intentionally annotated as unavailable; it does not fabricate a curve from all-fallback outputs.",
        "",
    ]
    (output_dir / "t26_local_only_report.md").write_text("\n".join(report_lines), encoding="utf-8")
    return sweep_json


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Produce local-only T26 dev diagnostics without external model calls.")
    parser.add_argument("--input", type=Path, required=True, help="Development ticket JSON file.")
    parser.add_argument("--run-dir", type=Path, required=True, help="T24 output directory with indexed results.jsonl.")
    parser.add_argument("--output", type=Path, required=True, help="Directory for T26 diagnostic artifacts.")
    args = parser.parse_args(argv)
    result = run_local_diagnostics(args.input, args.run_dir, args.output)
    print(json.dumps({
        "status": result["status"],
        "tickets": result["tickets"],
        "fallback_count": result["classification"]["fallback_count"],
        "confidence_calibration": result["classification"]["calibration_status"],
        "threshold_freeze": result["threshold_freeze"]["status"],
        "output": str(args.output.resolve()),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
