import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from src.store.decision_log import DecisionLogStore


REQUIRED_FIELDS = [
    "run_id",
    "ticket_id",
    "channel",
    "input_text_raw",
    "input_text_normalized",
    "input_hash",
    "input_metadata_json",
    "predicted_intent",
    "predicted_urgency",
    "intent_confidence",
    "urgency_confidence",
    "overall_confidence",
    "confidence_method",
    "classification_alternatives_json",
    "retrieval_query",
    "retrieval_results_json",
    "retrieved_source_ids_json",
    "retrieved_passages_json",
    "citation_ids_json",
    "corpus_version",
    "route_decision",
    "threshold_used",
    "route_reason_text",
    "response_sent",
    "final_action",
    "guardrail_checks_json",
    "guardrail_action",
    "guardrail_reason_text",
    "error_flags_json",
    "operator_readable_summary",
    "model_provider",
    "model_name",
    "prompt_versions_json",
    "latency_ms_total",
    "latency_breakdown_json",
]


def _run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "src.store.decision_log", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def test_20_sample_tickets_including_3_failures_log_in_finally(tmp_path):
    db_path = tmp_path / "decision_log.db"
    store = DecisionLogStore(db_path=db_path)
    run_id = "run-20"

    for i in range(1, 21):
        ticket_id = f"T-{i:03d}"
        error = None
        final_action = "answered"
        route_decision = "auto_answer"
        reason = "processed"
        try:
            if i in {3, 9, 17}:
                raise ValueError(f"simulated failure {i}")
        except Exception as e:
            error = e
            final_action = "failed_safe"
            route_decision = "fallback"
            reason = "failure handled"
        finally:
            store.log_terminal_outcome(
                run_id=run_id,
                ticket_id=ticket_id,
                channel="chat" if i % 2 == 0 else "email",
                final_action=final_action,
                route_decision=route_decision,
                route_reason_text=reason,
                input_text_raw=f"raw {i}",
                input_text_normalized=f"norm {i}",
                predicted_intent="demo",
                predicted_urgency="low",
                overall_confidence=0.1 if error else 0.95,
                guardrail_checks_json=[{"name": "pii", "passed": True}],
                guardrail_action="none",
                guardrail_reason_text="checked",
                operator_readable_summary=f"{ticket_id}:{final_action}",
                prompt_versions_json={"P-CLS-001": "v1.0.0", "P-GEN-001": "v1.0.0"},
                model_provider="simulation",
                model_name="demo-model",
                latency_ms_total=5,
                error=error,
            )

    assert store.count_by_run(run_id) == 20


def test_required_fields_populated(tmp_path):
    db_path = tmp_path / "decision_log.db"
    store = DecisionLogStore(db_path=db_path)
    run_id = "run-fields"
    store.log_terminal_outcome(
        run_id=run_id,
        ticket_id="T-REQ",
        channel="forum",
        final_action="escalated",
        route_decision="escalate",
        route_reason_text="insufficient evidence",
        input_text_raw="hello",
        input_text_normalized="hello",
    )
    rows = store.fetch_by_run(run_id)
    assert len(rows) == 1
    row = rows[0]
    for field in REQUIRED_FIELDS:
        assert field in row
        assert row[field] is not None

    # JSON/default fields must be populated and parseable where applicable.
    for json_field in (
        "input_metadata_json",
        "classification_alternatives_json",
        "retrieval_results_json",
        "retrieved_source_ids_json",
        "retrieved_passages_json",
        "citation_ids_json",
        "guardrail_checks_json",
        "error_flags_json",
        "prompt_versions_json",
        "latency_breakdown_json",
    ):
        assert isinstance(row[json_field], str) and row[json_field] != ""
        json.loads(row[json_field])

    # Key audit/decision fields should be explicitly populated for this logged outcome.
    assert row["route_reason_text"] == "insufficient evidence"
    assert row["operator_readable_summary"] != ""
    assert row["input_hash"] != ""


def test_reconcile_command_returns_ok_and_db_survives_restart(tmp_path):
    db_path = tmp_path / "decision_log.db"
    store = DecisionLogStore(db_path=db_path)
    run_id = "run-reconcile"

    for i in range(1, 21):
        err = RuntimeError("boom") if i in {2, 8, 15} else None
        try:
            if err:
                raise err
        except Exception as e:
            err = e
        finally:
            store.log_terminal_outcome(
                run_id=run_id,
                ticket_id=f"R-{i:03d}",
                channel="docs_comment",
                final_action="failed_safe" if err else "blocked" if i == 4 else "answered",
                route_decision="fallback" if err else "block" if i == 4 else "auto_answer",
                route_reason_text="ok" if not err else "error",
                input_text_raw=f"x{i}",
                input_text_normalized=f"x{i}",
                error=err,
            )

    # Restart/survive: reopen store from same DB path
    reopened = DecisionLogStore(db_path=db_path)
    assert reopened.count_by_run(run_id) == 20

    root = Path(__file__).resolve().parents[1]
    proc = _run_cli("--db", str(db_path), "reconcile", "--run-id", run_id, "--expected", "20", cwd=root)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OK" in (proc.stdout + proc.stderr)

    # Ensure SQLite file is readable and contains rows after reopen
    conn = sqlite3.connect(str(db_path))
    try:
        count = conn.execute("SELECT COUNT(*) FROM decision_log WHERE run_id=?", (run_id,)).fetchone()[0]
    finally:
        conn.close()
    assert count == 20
