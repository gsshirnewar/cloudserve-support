import json

from evaluation import harness


class FakePipeline:
    calls = 0

    def __init__(self, config, store):
        self.store = store

    def process_ticket(self, ticket, run_id, index):
        type(self).calls += 1
        if ticket.get("ticket_id") == "DEV-FAIL":
            raise RuntimeError("simulated per-ticket failure")

        classification = {
            "intent": "billing",
            "urgency": "low",
            "intent_confidence": 0.9,
            "urgency_confidence": 0.8,
            "overall_confidence": 0.85,
        }
        retrieval = {
            "hits": [{"doc_id": "DOC-1", "chunk_id": "DOC-1#chunk_1", "score": 0.9}],
        }
        validation = {
            "checks": [{"name": "pii_scan", "passed": True}],
            "passed": True,
            "pii_detected": False,
        }
        result = {
            "ticket_id": ticket["ticket_id"],
            "terminal_state": "answered",
            "classification": classification,
            "retrieval": retrieval,
            "route": {"route": "auto_answer"},
            "validation": validation,
            "errors": [],
            "degraded": False,
            "run_id": run_id,
        }
        self.store.write_decision({
            "run_id": run_id,
            "ticket_id": ticket["ticket_id"],
            "channel": ticket.get("channel", "unknown"),
            "final_action": "answered",
            "route_decision": "auto_answer",
            "route_reason_text": "test",
            "predicted_intent": "billing",
            "predicted_urgency": "low",
            "intent_confidence": 0.9,
            "urgency_confidence": 0.8,
            "overall_confidence": 0.85,
            "guardrail_checks_json": validation["checks"],
            "input_metadata_json": {"input_index": index, "run_id": run_id},
        })
        return result


def _write_tickets(path):
    tickets = [
        {
            "ticket_id": "DEV-1",
            "channel": "email",
            "body": "invoice",
            "labels": {"intent": "billing", "urgency": "low", "expected_doc_ids": ["DOC-1"]},
            "history": {"first_contact_resolution": True},
            "customer_tier": "standard",
        },
        {
            "ticket_id": "DEV-FAIL",
            "channel": "chat",
            "body": "provider failure",
        },
        {
            "ticket_id": "DEV-2",
            "channel": "forum",
            "body": "missing labels",
        },
    ]
    tickets.reverse()
    path.write_text(json.dumps(tickets), encoding="utf-8")
    return tickets


def test_harness_emits_metrics_and_tolerates_ticket_failure(tmp_path, monkeypatch, capsys):
    input_path = tmp_path / "renamed-input.json"
    output_path = tmp_path / "run"
    _write_tickets(input_path)
    FakePipeline.calls = 0
    monkeypatch.setattr(harness, "PipelineOrchestrator", FakePipeline)

    assert harness.run_harness(str(input_path), str(output_path), workers=2) == 0
    output = capsys.readouterr().out
    assert "reconciliation=OK" in output

    records = [json.loads(line) for line in (output_path / "results.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(records) == 3
    assert [row["input_index"] for row in records] == [0, 1, 2]
    assert records[1]["terminal_state"] == "escalated"
    assert records[1]["metrics_observation"]["degraded"] is True

    metrics = json.loads((output_path / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["volume"]["processed"] == 3
    assert metrics["volume"]["failed_or_degraded"] == 1
    assert metrics["technical"]["retrieval_hit_rate"] == 1.0
    assert metrics["technical"]["intent"]["evaluated_count"] == 1
    assert metrics["governance"]["decisions_logged"] == 3
    assert metrics["governance"]["tickets_processed_equals_decisions_logged"] is True
    assert (output_path / "metrics.md").exists()

    # A complete run can be resumed without rerunning its tickets.
    calls_after_first_run = FakePipeline.calls
    assert harness.run_harness(str(input_path), str(output_path), resume=True, workers=1) == 0
    assert FakePipeline.calls == calls_after_first_run


def test_resume_recovers_decision_logged_before_results_checkpoint(tmp_path, monkeypatch):
    input_path = tmp_path / "tickets.json"
    output_path = tmp_path / "interrupted-run"
    _write_tickets(input_path)
    FakePipeline.calls = 0
    monkeypatch.setattr(harness, "PipelineOrchestrator", FakePipeline)

    original_append = harness._append_result
    append_calls = 0

    def interrupt_after_decision_log(path, record):
        nonlocal append_calls
        append_calls += 1
        if append_calls == 1:
            raise OSError("simulated interruption before results checkpoint")
        original_append(path, record)

    monkeypatch.setattr(harness, "_append_result", interrupt_after_decision_log)
    assert harness.run_harness(str(input_path), str(output_path), workers=1) == 2
    calls_before_resume = FakePipeline.calls

    monkeypatch.setattr(harness, "_append_result", original_append)
    assert harness.run_harness(str(input_path), str(output_path), resume=True, workers=1) == 0
    assert FakePipeline.calls == calls_before_resume
    records = [json.loads(line) for line in (output_path / "results.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(records) == 3
    assert all(row["input_index"] in {0, 1, 2} for row in records)
    assert sum(bool(row["result"].get("recovered_from_decision_log")) for row in records) == 3
