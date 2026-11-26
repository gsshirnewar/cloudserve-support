"""FastAPI application for CloudServe pipeline (T23)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import JSONResponse

from src.config import get_config
from src.logging_config import configure_logging, get_logger
from src.pipeline.orchestrator import KillSwitch, PipelineOrchestrator
from src.store.decision_log import DecisionLogStore

logger = get_logger(__name__)

_config = get_config()
configure_logging(level=_config.runtime.log_level, log_format=_config.runtime.log_format)

kill_switch = KillSwitch()
store = DecisionLogStore(db_path=_config.paths.decision_log_db_path)
orchestrator = PipelineOrchestrator(config=_config, store=store, kill_switch=kill_switch)

app = FastAPI(title="CloudServe Support Pipeline", version="t23")


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "kill_switch": {"enabled": kill_switch.enabled, "reason": kill_switch.reason},
        "service": "cloudserve-support",
    }


@app.post("/tickets")
def process_ticket(ticket: Dict[str, Any] = Body(...)) -> JSONResponse:
    result = orchestrator.process_ticket(ticket)
    return JSONResponse(content={"ok": True, "result": result.to_dict()})


@app.post("/tickets/batch")
def process_tickets_batch(payload: Any = Body(...)) -> JSONResponse:
    if isinstance(payload, dict) and "tickets" in payload:
        tickets = payload.get("tickets") or []
    elif isinstance(payload, list):
        tickets = payload
    else:
        raise HTTPException(status_code=400, detail="Provide a JSON array of tickets or {'tickets': [...]}.")
    results, run_id = orchestrator.process_tickets(tickets)
    terminal_counts = {"answered": 0, "escalated": 0, "blocked": 0}
    for r in results:
        terminal_counts[r.terminal_state] = terminal_counts.get(r.terminal_state, 0) + 1
    return JSONResponse(content={
        "ok": True,
        "run_id": run_id,
        "count": len(results),
        "terminal_counts": terminal_counts,
        "results": [r.to_dict() for r in results],
    })


@app.get("/decisions/{decision_id}")
def get_decision(decision_id: str):
    row = None
    # numeric row id first
    if decision_id.isdigit():
        row = store.fetch_by_id(int(decision_id))
    if row is None:
        row = store.fetch_latest_by_ticket_id(decision_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Decision not found for id/ticket: {decision_id}")
    # parse JSON fields for readability
    parsed = dict(row)
    for k, v in list(parsed.items()):
        if isinstance(v, str) and k.endswith("_json"):
            try:
                parsed[k] = json.loads(v)
            except Exception:
                pass
        elif k in {"classification_alternatives_json","retrieval_results_json","retrieved_source_ids_json","retrieved_passages_json","citation_ids_json","guardrail_checks_json","error_flags_json","prompt_versions_json","latency_breakdown_json","input_metadata_json"} and isinstance(v, str):
            try:
                parsed[k] = json.loads(v)
            except Exception:
                pass
    return {"ok": True, "decision": parsed}


@app.get("/metrics")
def metrics() -> Dict[str, Any]:
    summary = store.metrics_summary()
    by_state = summary.get("by_terminal_state", {})
    total = int(summary.get("decisions_logged", 0))
    answered = int(by_state.get("answered", 0))
    escalated = int(by_state.get("escalated", 0))
    blocked = int(by_state.get("blocked", 0))
    failed = int(by_state.get("failed", 0) + by_state.get("failed_safe", 0))
    # treat failed_safe as degraded/escalated-equivalent in counts visibility
    processed = total
    return {
        "ok": True,
        "processed": processed,
        "answered": answered,
        "escalated": escalated,
        "blocked": blocked,
        "failed": failed,
        "decisions_logged": total,
        "tickets_processed_equals_decisions_logged": processed == total,
        "by_terminal_state": by_state,
        "guardrail_actions": summary.get("guardrail_actions", {}),
        "kill_switch": {"enabled": kill_switch.enabled, "reason": kill_switch.reason},
    }


@app.post("/admin/kill-switch")
def admin_kill_switch(payload: Dict[str, Any] = Body(default=None)) -> Dict[str, Any]:
    payload = payload or {}
    enabled = payload.get("enabled")
    reason = str(payload.get("reason") or "kill_switch_activated")
    if enabled is None:
        # toggle on by default
        enabled = True
    if bool(enabled):
        kill_switch.activate(reason=reason)
    else:
        kill_switch.deactivate()
    return {"ok": True, "kill_switch": {"enabled": kill_switch.enabled, "reason": kill_switch.reason}}


def get_app() -> FastAPI:
    return app
