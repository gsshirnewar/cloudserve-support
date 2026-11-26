"""Unattended, resumable ticket evaluation harness (T24)."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import os
import statistics
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.config import get_config
from src.logging_config import configure_logging, get_logger
from src.pipeline.orchestrator import PipelineOrchestrator
from src.store.decision_log import DecisionLogStore


logger = get_logger("evaluation.harness")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_tickets(path: Path) -> Tuple[List[Any], str]:
    raw_bytes = path.read_bytes()
    fingerprint = hashlib.sha256(raw_bytes).hexdigest()
    text = raw_bytes.decode("utf-8-sig")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as json_error:
        tickets = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                tickets.append(json.loads(line))
            except json.JSONDecodeError as line_error:
                raise ValueError(
                    f"Input is neither JSON nor valid JSONL; invalid JSONL at line {line_number}: {line_error}"
                ) from json_error
        if not tickets:
            raise ValueError(f"Input contains no JSON tickets: {path}") from json_error
        return tickets, fingerprint

    if isinstance(payload, list):
        return payload, fingerprint
    if isinstance(payload, dict) and isinstance(payload.get("tickets"), list):
        return payload["tickets"], fingerprint
    return [payload], fingerprint


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(str(temporary), str(path))


def _read_results(path: Path) -> Dict[int, Dict[str, Any]]:
    if not path.exists():
        return {}
    data = path.read_bytes()
    records: Dict[int, Dict[str, Any]] = {}
    offset = 0
    lines = data.splitlines(keepends=True)
    for position, line in enumerate(lines):
        line_end = offset + len(line)
        try:
            row = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            is_incomplete_tail = position == len(lines) - 1 and not line.endswith((b"\n", b"\r"))
            if not is_incomplete_tail:
                raise ValueError(f"Invalid results.jsonl record ending at byte {line_end}: {error}") from error
            with path.open("r+b") as results_file:
                results_file.truncate(offset)
            break
        if not isinstance(row, dict) or not isinstance(row.get("input_index"), int):
            raise ValueError(f"Invalid results.jsonl record ending at byte {line_end}: missing integer input_index")
        records[row["input_index"]] = row
        offset = line_end
    return records


def _append_result(path: Path, record: Mapping[str, Any]) -> None:
    encoded = (json.dumps(record, ensure_ascii=False, separators=(",", ":"), default=str) + "\n").encode("utf-8")
    with path.open("ab") as results_file:
        results_file.write(encoded)
        results_file.flush()
        os.fsync(results_file.fileno())


def _compact_results(path: Path, records: Mapping[int, Mapping[str, Any]]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as results_file:
        for index in sorted(records):
            results_file.write(json.dumps(records[index], ensure_ascii=False, separators=(",", ":"), default=str))
            results_file.write("\n")
        results_file.flush()
        os.fsync(results_file.fileno())
    os.replace(str(temporary), str(path))


def _parse_json_field(value: Any, default: Any) -> Any:
    if not isinstance(value, str):
        return value if value is not None else default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _decision_index(row: Mapping[str, Any]) -> Optional[int]:
    metadata = _parse_json_field(row.get("input_metadata_json"), {})
    if isinstance(metadata, dict) and isinstance(metadata.get("input_index"), int):
        return metadata["input_index"]
    return None


def _to_dict(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return dict(value)
    return value


def _mapping(value: Any) -> Dict[str, Any]:
    converted = _to_dict(value)
    return dict(converted) if isinstance(converted, Mapping) else {}


def _metric_observation(ticket: Any, result: Mapping[str, Any], processing_ms: float) -> Dict[str, Any]:
    raw = dict(ticket) if isinstance(ticket, Mapping) else {}
    labels = raw.get("labels") if isinstance(raw.get("labels"), dict) else {}
    history = raw.get("history") if isinstance(raw.get("history"), dict) else {}
    customer = raw.get("customer") if isinstance(raw.get("customer"), dict) else {}
    classification = result.get("classification") if isinstance(result.get("classification"), dict) else {}
    retrieval = result.get("retrieval") if isinstance(result.get("retrieval"), dict) else {}
    route = result.get("route") if isinstance(result.get("route"), dict) else {}
    validation = result.get("validation") if isinstance(result.get("validation"), dict) else {}
    hits = retrieval.get("hits") if isinstance(retrieval.get("hits"), list) else []
    checks = validation.get("checks") if isinstance(validation.get("checks"), list) else []

    expected_docs = labels.get("expected_doc_ids")
    if not isinstance(expected_docs, list):
        expected_docs = []
    retrieved_docs = []
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        doc_id = hit.get("doc_id")
        if not doc_id and isinstance(hit.get("chunk_id"), str):
            doc_id = hit["chunk_id"].split("#", 1)[0]
        if doc_id:
            retrieved_docs.append(str(doc_id))

    return {
        "channel": raw.get("channel") or "unknown",
        "intent_label": labels.get("intent"),
        "intent_prediction": classification.get("intent"),
        "intent_confidence": classification.get("intent_confidence"),
        "urgency_label": labels.get("urgency"),
        "urgency_prediction": classification.get("urgency"),
        "expected_doc_ids": [str(item) for item in expected_docs if item],
        "retrieved_doc_ids": retrieved_docs,
        "first_contact_resolution": history.get("first_contact_resolution"),
        "terminal_state": result.get("terminal_state", "escalated"),
        "processing_ms": round(float(processing_ms), 3),
        "guardrail_checks": checks,
        "pii_detected": bool(validation.get("pii_detected")),
        "customer_tier": customer.get("customer_tier", raw.get("customer_tier")),
        "customer_region": customer.get("customer_region", raw.get("customer_region")),
        "language_fluency": customer.get("language_fluency", raw.get("language_fluency")),
        "route": route.get("route"),
        "degraded": bool(result.get("degraded") or result.get("errors")),
    }


def _make_record(
    index: int,
    ticket: Any,
    run_id: str,
    result: Mapping[str, Any],
    processing_ms: float,
) -> Dict[str, Any]:
    record = {
        "input_index": index,
        "ticket_id": result.get("ticket_id") or (
            ticket.get("ticket_id") if isinstance(ticket, Mapping) else f"EVAL-{index:06d}"
        ),
        "run_id": run_id,
        "terminal_state": result.get("terminal_state", "escalated"),
        "processing_ms": round(float(processing_ms), 3),
        "result": dict(result),
    }
    record["metrics_observation"] = _metric_observation(ticket, result, processing_ms)
    return record


def _recover_record(index: int, ticket: Any, run_id: str, row: Mapping[str, Any]) -> Dict[str, Any]:
    checks = _parse_json_field(row.get("guardrail_checks_json"), [])
    retrieval_hits = _parse_json_field(row.get("retrieval_results_json"), [])
    errors = _parse_json_field(row.get("error_flags_json"), [])
    intent = row.get("predicted_intent")
    urgency = row.get("predicted_urgency")
    validation = {
        "checks": checks if isinstance(checks, list) else [],
        "passed": not any(isinstance(c, dict) and not c.get("passed", True) for c in checks or []),
        "pii_detected": any(
            isinstance(c, dict) and "pii" in str(c.get("name", "")).lower() and not c.get("passed", True)
            for c in checks or []
        ),
    }
    recovered = {
        "ticket_id": row.get("ticket_id"),
        "terminal_state": row.get("final_action", "escalated"),
        "answer": {"answer_text": row.get("generated_answer_final") or row.get("generated_answer_draft") or ""},
        "classification": {
            "intent": intent,
            "urgency": urgency,
            "intent_confidence": row.get("intent_confidence"),
            "urgency_confidence": row.get("urgency_confidence"),
            "overall_confidence": row.get("overall_confidence"),
        },
        "retrieval": {"hits": retrieval_hits if isinstance(retrieval_hits, list) else []},
        "route": {"route": row.get("route_decision"), "reason": row.get("route_reason_text")},
        "validation": validation,
        "decision_row_id": row.get("id"),
        "run_id": run_id,
        "errors": errors if isinstance(errors, list) else [],
        "degraded": bool(errors),
        "recovered_from_decision_log": True,
    }
    return _make_record(index, ticket, run_id, recovered, float(row.get("latency_ms_total") or 0))


def _class_metrics(observations: Sequence[Mapping[str, Any]], label_key: str, prediction_key: str) -> Dict[str, Any]:
    pairs = [
        (str(row[label_key]), str(row[prediction_key]))
        for row in observations
        if row.get(label_key) not in (None, "") and row.get(prediction_key) not in (None, "")
    ]
    labels = sorted({label for label, _ in pairs} | {prediction for _, prediction in pairs})
    per_class: Dict[str, Any] = {}
    for label in labels:
        true_positive = sum(actual == label and predicted == label for actual, predicted in pairs)
        false_positive = sum(actual != label and predicted == label for actual, predicted in pairs)
        false_negative = sum(actual == label and predicted != label for actual, predicted in pairs)
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
            "support": sum(actual == label for actual, _ in pairs),
        }
    return {
        "evaluated_count": len(pairs),
        "accuracy": sum(actual == predicted for actual, predicted in pairs) / len(pairs) if pairs else None,
        "per_class": per_class,
    }


def _calibration_metrics(observations: Sequence[Mapping[str, Any]], bins: int = 10) -> Dict[str, Any]:
    samples = []
    for row in observations:
        label, prediction, confidence = (
            row.get("intent_label"),
            row.get("intent_prediction"),
            row.get("intent_confidence"),
        )
        if label in (None, "") or prediction in (None, "") or confidence is None:
            continue
        try:
            score = float(confidence)
        except (TypeError, ValueError):
            continue
        if 0.0 <= score <= 1.0:
            samples.append((score, str(label) == str(prediction)))
    bin_rows = []
    weighted_gap = 0.0
    for index in range(bins):
        lower = index / bins
        upper = (index + 1) / bins
        members = [
            (score, correct)
            for score, correct in samples
            if lower <= score < upper or (index == bins - 1 and score == 1.0)
        ]
        if members:
            mean_confidence = sum(score for score, _ in members) / len(members)
            accuracy = sum(correct for _, correct in members) / len(members)
            gap = abs(mean_confidence - accuracy)
            weighted_gap += len(members) / len(samples) * gap
        else:
            mean_confidence = None
            accuracy = None
            gap = None
        bin_rows.append({
            "lower": lower,
            "upper": upper,
            "count": len(members),
            "mean_confidence": mean_confidence,
            "accuracy": accuracy,
            "gap": gap,
        })
    return {"count": len(samples), "ece": weighted_gap if samples else None, "bins": bin_rows}


def _percentile(values: Sequence[float], percentile: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    position = percentile * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _fairness_slices(observations: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    dimensions = ("channel", "customer_tier", "customer_region", "language_fluency")
    report: Dict[str, Any] = {}
    for dimension in dimensions:
        groups: Dict[str, List[Mapping[str, Any]]] = {}
        for row in observations:
            value = row.get(dimension)
            if value not in (None, ""):
                groups.setdefault(str(value), []).append(row)
        report[dimension] = {}
        for value, rows in sorted(groups.items()):
            labelled = [
                row for row in rows
                if row.get("intent_label") not in (None, "") and row.get("intent_prediction") not in (None, "")
            ]
            report[dimension][value] = {
                "count": len(rows),
                "answered_rate": sum(row.get("terminal_state") == "answered" for row in rows) / len(rows),
                "escalation_rate": sum(row.get("terminal_state") in {"escalated", "blocked"} for row in rows) / len(rows),
                "intent_accuracy": (
                    sum(str(row["intent_label"]) == str(row["intent_prediction"]) for row in labelled) / len(labelled)
                    if labelled else None
                ),
                "intent_labelled_count": len(labelled),
            }
    return report


def _build_metrics(records: Sequence[Mapping[str, Any]], logged_count: int, expected_count: int) -> Dict[str, Any]:
    observations = [
        row.get("metrics_observation", {})
        for row in records
        if isinstance(row.get("metrics_observation"), dict)
    ]
    states = [str(row.get("terminal_state") or "escalated") for row in records]
    latencies = [float(row.get("processing_ms") or 0.0) for row in records]
    all_guardrails: Dict[str, int] = {}
    pii_detected = 0
    for row in observations:
        detected = bool(row.get("pii_detected"))
        for check in row.get("guardrail_checks", []):
            if not isinstance(check, dict) or check.get("passed", True):
                continue
            name = str(check.get("name") or "unknown")
            all_guardrails[name] = all_guardrails.get(name, 0) + 1
            if "pii" in name.lower():
                detected = True
        pii_detected += int(detected)

    retrieval_rows = [row for row in observations if row.get("expected_doc_ids")]
    retrieval_hits = sum(
        bool(set(row.get("expected_doc_ids", [])) & set(row.get("retrieved_doc_ids", [])))
        for row in retrieval_rows
    )
    fcr_values = [row.get("first_contact_resolution") for row in observations if isinstance(row.get("first_contact_resolution"), bool)]
    return {
        "volume": {
            "input_tickets": expected_count,
            "processed": len(records),
            "answered": states.count("answered"),
            "escalated": states.count("escalated"),
            "blocked": states.count("blocked"),
            "failed_or_degraded": sum(bool(row.get("metrics_observation", {}).get("degraded")) for row in records),
        },
        "business": {
            "fcr_proxy_answered_rate": states.count("answered") / len(states) if states else None,
            "historical_fcr_rate": sum(fcr_values) / len(fcr_values) if fcr_values else None,
            "historical_fcr_label_count": len(fcr_values),
            "escalation_rate": sum(state in {"escalated", "blocked"} for state in states) / len(states) if states else None,
            "processing_time_ms_mean": statistics.mean(latencies) if latencies else None,
            "processing_time_ms_median": statistics.median(latencies) if latencies else None,
        },
        "technical": {
            "intent": _class_metrics(observations, "intent_label", "intent_prediction"),
            "urgency": _class_metrics(observations, "urgency_label", "urgency_prediction"),
            "retrieval_hit_rate": retrieval_hits / len(retrieval_rows) if retrieval_rows else None,
            "retrieval_evaluated_count": len(retrieval_rows),
            "latency_ms_p50": _percentile(latencies, 0.50),
            "latency_ms_p95": _percentile(latencies, 0.95),
        },
        "calibration": {"intent_confidence": _calibration_metrics(observations)},
        "governance": {
            "decisions_logged": logged_count,
            "tickets_processed_equals_decisions_logged": len(records) == logged_count == expected_count,
            "guardrail_activations_by_type": all_guardrails,
            "pii_detections": pii_detected,
        },
        "fairness_slices": _fairness_slices(observations),
        "label_coverage": {
            "intent": sum(row.get("intent_label") not in (None, "") for row in observations),
            "urgency": sum(row.get("urgency_label") not in (None, "") for row in observations),
            "expected_docs": len(retrieval_rows),
        },
        "notes": [
            "FCR proxy is the answered share; historical FCR is reported separately from supplied history labels.",
            "Classification and calibration metrics exclude tickets without the corresponding labels.",
            "Fairness slices are descriptive and include sample counts; small groups should not be over-interpreted.",
        ],
    }


def _metrics_markdown(metrics: Mapping[str, Any], run_id: str) -> str:
    volume = metrics["volume"]
    business = metrics["business"]
    technical = metrics["technical"]
    governance = metrics["governance"]

    def show(value: Any) -> str:
        return "n/a" if value is None else (f"{value:.4f}" if isinstance(value, float) else str(value))

    lines = [
        "# Evaluation metrics",
        "",
        f"- Run ID: `{run_id}`",
        f"- Reconciliation: **{'PASS' if governance['tickets_processed_equals_decisions_logged'] else 'FAIL'}**",
        "",
        "## Volume and business metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Input / processed | {volume['input_tickets']} / {volume['processed']} |",
        f"| Answered / escalated / blocked | {volume['answered']} / {volume['escalated']} / {volume['blocked']} |",
        f"| Failed or degraded | {volume['failed_or_degraded']} |",
        f"| FCR proxy (answered share) | {show(business['fcr_proxy_answered_rate'])} |",
        f"| Historical FCR label rate (n={business['historical_fcr_label_count']}) | {show(business['historical_fcr_rate'])} |",
        f"| Escalation rate | {show(business['escalation_rate'])} |",
        f"| Processing time mean / median (ms) | {show(business['processing_time_ms_mean'])} / {show(business['processing_time_ms_median'])} |",
        "",
        "## Technical metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Intent accuracy (n={technical['intent']['evaluated_count']}) | {show(technical['intent']['accuracy'])} |",
        f"| Urgency accuracy (n={technical['urgency']['evaluated_count']}) | {show(technical['urgency']['accuracy'])} |",
        f"| Retrieval hit rate (n={technical['retrieval_evaluated_count']}) | {show(technical['retrieval_hit_rate'])} |",
        f"| Latency p50 / p95 (ms) | {show(technical['latency_ms_p50'])} / {show(technical['latency_ms_p95'])} |",
        f"| Intent confidence ECE (n={metrics['calibration']['intent_confidence']['count']}) | {show(metrics['calibration']['intent_confidence']['ece'])} |",
        "",
        "## Governance",
        "",
        f"- Decisions logged: {governance['decisions_logged']}",
        f"- PII detections: {governance['pii_detections']}",
        f"- Failed guardrail checks: `{json.dumps(governance['guardrail_activations_by_type'], sort_keys=True)}`",
        "",
        "## Fairness slices",
        "",
        "See `metrics.json` for counts, answered/escalation rates, and labelled intent accuracy by channel, tier, region, and language fluency.",
        "",
        "> Metrics with no eligible labels are `null`/`n/a`; they are not treated as zero.",
        "",
    ]
    return "\n".join(lines)


def _record_from_exception(
    index: int,
    ticket: Any,
    run_id: str,
    error: Exception,
    store: DecisionLogStore,
) -> Dict[str, Any]:
    raw = dict(ticket) if isinstance(ticket, Mapping) else {}
    ticket_id = str(raw.get("ticket_id") or raw.get("id") or f"EVAL-{index:06d}")
    try:
        row_id = store.log_terminal_outcome(
            run_id=run_id,
            ticket_id=ticket_id,
            channel=str(raw.get("channel") or "unknown"),
            final_action="escalated",
            route_decision="fallback",
            route_reason_text="harness_caught_ticket_failure",
            input_text_raw=str(raw.get("body") or ""),
            input_text_normalized=str(raw.get("body") or ""),
            operator_readable_summary=f"{ticket_id}: escalated after processing failure",
            error=error,
            input_metadata_json={"input_index": index, "run_id": run_id},
        )
    except Exception as log_error:
        raise RuntimeError(f"Ticket {ticket_id} failed and its fallback decision could not be logged: {log_error}") from error
    result = {
        "ticket_id": ticket_id,
        "terminal_state": "escalated",
        "decision_row_id": row_id,
        "run_id": run_id,
        "errors": [{"node": "harness", "type": type(error).__name__, "message": str(error)}],
        "degraded": True,
    }
    return _make_record(index, ticket, run_id, result, 0.0)


def _write_progress_manifest(path: Path, manifest: Dict[str, Any], records: Mapping[int, Mapping[str, Any]]) -> None:
    manifest["completed_count"] = len(records)
    manifest["updated_at"] = _utc_now()
    _atomic_write_json(path, manifest)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m evaluation.harness",
        description="Run the CloudServe evaluation harness on a ticket dataset.",
    )
    parser.add_argument("--input", required=True, help="Path to JSON/JSONL ticket data.")
    parser.add_argument("--output", required=True, help="Directory for results, metrics, and the run decision log.")
    parser.add_argument("--resume", action="store_true", help="Resume a matching run from its checkpointed output directory.")
    parser.add_argument("--max-tickets", type=int, default=None, help="Optional limit for local smoke runs.")
    parser.add_argument("--workers", type=int, default=None, help="Maximum concurrent ticket executions.")
    return parser


def run_harness(
    input_path: str,
    output_path: str,
    resume: bool = False,
    max_tickets: Optional[int] = None,
    workers: Optional[int] = None,
) -> int:
    config = get_config()
    configure_logging(level=config.runtime.log_level, log_format=config.runtime.log_format)

    try:
        in_path = Path(input_path)
        tickets, input_hash = _load_tickets(in_path)
        if max_tickets is not None and max_tickets < 0:
            raise ValueError("--max-tickets must be non-negative")
        selected = tickets[:max_tickets] if max_tickets is not None else tickets
        worker_count = workers if workers is not None else config.runtime.max_concurrency
        if worker_count < 1:
            raise ValueError("--workers must be at least 1")

        out_dir = Path(output_path)
        out_dir.mkdir(parents=True, exist_ok=True)
        results_path = out_dir / "results.jsonl"
        manifest_path = out_dir / "run_manifest.json"
        db_path = out_dir / "decision_log.db"

        if resume:
            if not manifest_path.exists():
                raise FileNotFoundError(f"Cannot resume: run manifest not found at {manifest_path}")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("input_sha256") != input_hash:
                raise ValueError("Cannot resume: input file content differs from the original run.")
            if manifest.get("selected_ticket_count") != len(selected):
                raise ValueError("Cannot resume: selected ticket count differs from the original run.")
            if manifest.get("max_tickets") != max_tickets:
                raise ValueError("Cannot resume: --max-tickets differs from the original run.")
            run_id = str(manifest["run_id"])
        else:
            existing = [p for p in (manifest_path, results_path, db_path) if p.exists()]
            if existing:
                raise FileExistsError(
                    f"Output directory already contains run artifacts ({existing[0]}). Use --resume or choose a new directory."
                )
            run_id = f"eval-{uuid.uuid4().hex[:12]}"
            manifest = {
                "run_id": run_id,
                "status": "running",
                "input_path": str(in_path.resolve()),
                "input_sha256": input_hash,
                "input_ticket_count": len(tickets),
                "selected_ticket_count": len(selected),
                "max_tickets": max_tickets,
                "workers": worker_count,
                "started_at": _utc_now(),
                "completed_count": 0,
            }
            _atomic_write_json(manifest_path, manifest)

        store = DecisionLogStore(db_path=db_path)
        pipeline = PipelineOrchestrator(config=config, store=store)
        records_by_index = _read_results(results_path) if resume else {}

        for index, row in list(records_by_index.items()):
            if index < 0 or index >= len(selected):
                raise ValueError(f"Checkpoint contains out-of-range input_index {index}")
            if row.get("run_id") != run_id:
                raise ValueError(f"Checkpoint record {index} belongs to a different run.")

        logged_by_index: Dict[int, Dict[str, Any]] = {}
        if resume:
            for decision in store.fetch_by_run(run_id):
                index = _decision_index(decision)
                if index is not None and 0 <= index < len(selected):
                    logged_by_index[index] = decision
            for index, decision in logged_by_index.items():
                if index not in records_by_index:
                    recovered = _recover_record(index, selected[index], run_id, decision)
                    records_by_index[index] = recovered
                    _append_result(results_path, recovered)

        pending = [
            (index, ticket)
            for index, ticket in enumerate(selected)
            if index not in records_by_index or index not in logged_by_index
        ]
        _write_progress_manifest(manifest_path, manifest, records_by_index)

        def process_one(index: int, ticket: Any) -> Dict[str, Any]:
            started = time.perf_counter()
            try:
                result_obj = pipeline.process_ticket(ticket, run_id=run_id, index=index)
                result = _mapping(result_obj)
                duration = (time.perf_counter() - started) * 1000.0
                return _make_record(index, ticket, run_id, result, duration)
            except Exception as error:
                duration = (time.perf_counter() - started) * 1000.0
                for decision in store.fetch_by_run(run_id):
                    if _decision_index(decision) == index:
                        recovered = _recover_record(index, ticket, run_id, decision)
                        recovered["processing_ms"] = round(duration, 3)
                        recovered["metrics_observation"]["processing_ms"] = round(duration, 3)
                        return recovered
                failed = _record_from_exception(index, ticket, run_id, error, store)
                failed["processing_ms"] = round(duration, 3)
                failed["metrics_observation"]["processing_ms"] = round(duration, 3)
                return failed

        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {executor.submit(process_one, index, ticket): index for index, ticket in pending}
            for future in concurrent.futures.as_completed(futures):
                record = future.result()
                index = int(record["input_index"])
                _append_result(results_path, record)
                records_by_index[index] = record
                _write_progress_manifest(manifest_path, manifest, records_by_index)
                logger.info(
                    "Evaluation ticket completed",
                    extra={
                        "event": "evaluation_ticket_completed",
                        "component": "evaluation.harness",
                        "ticket_id": record.get("ticket_id"),
                        "outcome": record.get("terminal_state"),
                        "input_index": index,
                    },
                )

        _compact_results(results_path, records_by_index)
        reconciliation = store.reconcile(run_id, expected_processed=len(selected))
        ordered_records = [records_by_index[index] for index in sorted(records_by_index)]
        metrics = _build_metrics(ordered_records, logged_count=reconciliation.logged_count, expected_count=len(selected))
        metrics["run"] = {
            "run_id": run_id,
            "input_sha256": input_hash,
            "started_at": manifest.get("started_at"),
            "completed_at": _utc_now(),
            "reconciliation": {
                "ok": reconciliation.ok,
                "expected_processed": reconciliation.expected_processed,
                "logged_count": reconciliation.logged_count,
                "distinct_ticket_count": reconciliation.distinct_ticket_count,
                "message": reconciliation.message,
            },
        }
        _atomic_write_json(out_dir / "metrics.json", metrics)
        (out_dir / "metrics.md").write_text(_metrics_markdown(metrics, run_id), encoding="utf-8")

        manifest["status"] = "complete" if reconciliation.ok else "failed_reconciliation"
        manifest["completed_at"] = _utc_now()
        manifest["completed_count"] = len(records_by_index)
        manifest["reconciliation"] = metrics["run"]["reconciliation"]
        _atomic_write_json(manifest_path, manifest)

        print(
            f"[harness] run_id={run_id} processed={len(records_by_index)}/{len(selected)} "
            f"decisions_logged={reconciliation.logged_count} reconciliation={'OK' if reconciliation.ok else 'FAIL'}"
        )
        print(f"[harness] results={results_path}")
        print(f"[harness] metrics={out_dir / 'metrics.json'}")
        return 0 if reconciliation.ok and len(records_by_index) == len(selected) else 1
    except Exception as error:
        logger.exception("Evaluation harness failed", extra={"component": "evaluation.harness"})
        print(f"[harness:error] {type(error).__name__}: {error}")
        return 2


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    return run_harness(
        input_path=args.input,
        output_path=args.output,
        resume=args.resume,
        max_tickets=args.max_tickets,
        workers=args.workers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
