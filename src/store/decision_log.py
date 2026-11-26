"""SQLite decision log store and reconciliation utilities (T17, A8)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence

from src.config import get_config
from src.logging_config import configure_logging, get_logger

logger = get_logger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _coerce_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    return str(value)


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


@dataclass
class ReconcileResult:
    ok: bool
    run_id: str
    expected_processed: int
    logged_count: int
    distinct_ticket_count: int
    message: str


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS decision_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    ticket_id TEXT NOT NULL,
    attempt_no INTEGER NOT NULL DEFAULT 1,
    processed_at TEXT NOT NULL,
    received_at TEXT,
    channel TEXT NOT NULL,
    input_text_raw TEXT NOT NULL DEFAULT '',
    input_text_normalized TEXT NOT NULL DEFAULT '',
    input_hash TEXT NOT NULL DEFAULT '',
    input_metadata_json TEXT NOT NULL DEFAULT '{}',
    predicted_intent TEXT NOT NULL DEFAULT 'unknown_fallback',
    predicted_urgency TEXT NOT NULL DEFAULT 'unknown_fallback',
    intent_confidence REAL NOT NULL DEFAULT 0.0,
    urgency_confidence REAL NOT NULL DEFAULT 0.0,
    overall_confidence REAL NOT NULL DEFAULT 0.0,
    confidence_method TEXT NOT NULL DEFAULT 'not_set',
    classification_alternatives_json TEXT NOT NULL DEFAULT '[]',
    retrieval_query TEXT NOT NULL DEFAULT '',
    retrieval_results_json TEXT NOT NULL DEFAULT '[]',
    retrieved_source_ids_json TEXT NOT NULL DEFAULT '[]',
    retrieved_passages_json TEXT NOT NULL DEFAULT '[]',
    citation_ids_json TEXT NOT NULL DEFAULT '[]',
    corpus_version TEXT NOT NULL DEFAULT 'unknown',
    route_decision TEXT NOT NULL DEFAULT 'fallback',
    threshold_used REAL NOT NULL DEFAULT 0.0,
    route_reason_text TEXT NOT NULL DEFAULT '',
    generated_answer_draft TEXT,
    generated_answer_final TEXT,
    response_sent INTEGER NOT NULL DEFAULT 0,
    final_action TEXT NOT NULL DEFAULT 'failed_safe',
    guardrail_checks_json TEXT NOT NULL DEFAULT '[]',
    guardrail_action TEXT NOT NULL DEFAULT 'none',
    guardrail_reason_text TEXT NOT NULL DEFAULT '',
    escalation_payload_json TEXT,
    fallback_reason_text TEXT,
    error_flags_json TEXT NOT NULL DEFAULT '[]',
    operator_readable_summary TEXT NOT NULL DEFAULT '',
    model_provider TEXT NOT NULL DEFAULT 'n/a',
    model_name TEXT NOT NULL DEFAULT 'n/a',
    prompt_versions_json TEXT NOT NULL DEFAULT '{}',
    code_version TEXT,
    latency_ms_total INTEGER NOT NULL DEFAULT 0,
    latency_breakdown_json TEXT NOT NULL DEFAULT '{}',
    determinism_key TEXT
);
CREATE INDEX IF NOT EXISTS idx_decision_log_run_id ON decision_log(run_id);
CREATE INDEX IF NOT EXISTS idx_decision_log_run_ticket ON decision_log(run_id, ticket_id);
CREATE INDEX IF NOT EXISTS idx_decision_log_final_action ON decision_log(final_action);
"""


class DecisionLogStore:
    def __init__(self, db_path: Optional[Path | str] = None):
        if db_path is None:
            db_path = get_config().paths.decision_log_db_path
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def ensure_schema(self) -> None:
        with self.connection() as conn:
            conn.executescript(SCHEMA_SQL)

    @staticmethod
    def _normalize_record(record: Mapping[str, Any]) -> Dict[str, Any]:
        now = _utc_now_iso()
        run_id = _coerce_text(record.get("run_id"), "default-run")
        ticket_id = _coerce_text(record.get("ticket_id"), "unknown-ticket")
        channel = _coerce_text(record.get("channel"), "unknown")
        input_text_raw = _coerce_text(record.get("input_text_raw"), "")
        input_text_normalized = _coerce_text(record.get("input_text_normalized"), "")
        input_hash = _coerce_text(record.get("input_hash"), "") or _hash_text(
            input_text_normalized or input_text_raw or ticket_id
        )

        payload: Dict[str, Any] = {
            "run_id": run_id,
            "ticket_id": ticket_id,
            "attempt_no": int(record.get("attempt_no") or 1),
            "processed_at": _coerce_text(record.get("processed_at"), now),
            "received_at": record.get("received_at"),
            "channel": channel,
            "input_text_raw": input_text_raw,
            "input_text_normalized": input_text_normalized,
            "input_hash": input_hash,
            "input_metadata_json": _json_dumps(record.get("input_metadata_json") or {}),
            "predicted_intent": _coerce_text(record.get("predicted_intent"), "unknown_fallback"),
            "predicted_urgency": _coerce_text(record.get("predicted_urgency"), "unknown_fallback"),
            "intent_confidence": float(record.get("intent_confidence") or 0.0),
            "urgency_confidence": float(record.get("urgency_confidence") or 0.0),
            "overall_confidence": float(record.get("overall_confidence") or 0.0),
            "confidence_method": _coerce_text(record.get("confidence_method"), "not_set"),
            "classification_alternatives_json": _json_dumps(record.get("classification_alternatives_json") or []),
            "retrieval_query": _coerce_text(record.get("retrieval_query"), ""),
            "retrieval_results_json": _json_dumps(record.get("retrieval_results_json") or []),
            "retrieved_source_ids_json": _json_dumps(record.get("retrieved_source_ids_json") or []),
            "retrieved_passages_json": _json_dumps(record.get("retrieved_passages_json") or []),
            "citation_ids_json": _json_dumps(record.get("citation_ids_json") or []),
            "corpus_version": _coerce_text(record.get("corpus_version"), "unknown"),
            "route_decision": _coerce_text(record.get("route_decision"), "fallback"),
            "threshold_used": float(record.get("threshold_used") or 0.0),
            "route_reason_text": _coerce_text(record.get("route_reason_text"), ""),
            "generated_answer_draft": record.get("generated_answer_draft"),
            "generated_answer_final": record.get("generated_answer_final"),
            "response_sent": 1 if bool(record.get("response_sent")) else 0,
            "final_action": _coerce_text(record.get("final_action"), "failed_safe"),
            "guardrail_checks_json": _json_dumps(record.get("guardrail_checks_json") or []),
            "guardrail_action": _coerce_text(record.get("guardrail_action"), "none"),
            "guardrail_reason_text": _coerce_text(record.get("guardrail_reason_text"), ""),
            "escalation_payload_json": _json_dumps(record.get("escalation_payload_json"))
            if record.get("escalation_payload_json") is not None
            else None,
            "fallback_reason_text": record.get("fallback_reason_text"),
            "error_flags_json": _json_dumps(record.get("error_flags_json") or []),
            "operator_readable_summary": _coerce_text(
                record.get("operator_readable_summary"),
                f"{ticket_id}:{_coerce_text(record.get('final_action'), 'failed_safe')}",
            ),
            "model_provider": _coerce_text(record.get("model_provider"), "n/a"),
            "model_name": _coerce_text(record.get("model_name"), "n/a"),
            "prompt_versions_json": _json_dumps(record.get("prompt_versions_json") or {}),
            "code_version": record.get("code_version"),
            "latency_ms_total": int(record.get("latency_ms_total") or 0),
            "latency_breakdown_json": _json_dumps(record.get("latency_breakdown_json") or {}),
            "determinism_key": record.get("determinism_key"),
        }
        return payload

    def write_decision(self, record: Mapping[str, Any]) -> int:
        """Append one decision record and return inserted row id."""
        payload = self._normalize_record(record)
        columns = list(payload.keys())
        placeholders = ", ".join(["?"] * len(columns))
        sql = f"INSERT INTO decision_log ({', '.join(columns)}) VALUES ({placeholders})"
        values = [payload[c] for c in columns]
        with self.connection() as conn:
            cur = conn.execute(sql, values)
            row_id = int(cur.lastrowid)
        logger.info(
            "Decision logged",
            extra={
                "component": "store.decision_log",
                "event": "decision_logged",
                "ticket_id": payload["ticket_id"],
                "outcome": payload["final_action"],
            },
        )
        return row_id

    def log_terminal_outcome(
        self,
        *,
        run_id: str,
        ticket_id: str,
        channel: str = "unknown",
        final_action: str = "failed_safe",
        route_decision: str = "fallback",
        route_reason_text: str = "",
        predicted_intent: str = "unknown_fallback",
        predicted_urgency: str = "unknown_fallback",
        overall_confidence: float = 0.0,
        input_text_raw: str = "",
        input_text_normalized: str = "",
        operator_readable_summary: Optional[str] = None,
        error: Optional[BaseException] = None,
        **extra: Any,
    ) -> int:
        """Convenience writer intended for use in `finally` blocks."""
        error_flags = list(extra.pop("error_flags_json", []) or [])
        fallback_reason = extra.pop("fallback_reason_text", None)
        if error is not None:
            error_flags.append({"type": type(error).__name__, "message": str(error)})
            fallback_reason = fallback_reason or f"{type(error).__name__}: {error}"
            if not route_reason_text:
                route_reason_text = "Processing failed; safe fallback logged."
            if not operator_readable_summary:
                operator_readable_summary = f"{ticket_id}: failed_safe ({type(error).__name__})"
        record = {
            "run_id": run_id,
            "ticket_id": ticket_id,
            "channel": channel,
            "final_action": final_action,
            "route_decision": route_decision,
            "route_reason_text": route_reason_text,
            "predicted_intent": predicted_intent,
            "predicted_urgency": predicted_urgency,
            "overall_confidence": overall_confidence,
            "input_text_raw": input_text_raw,
            "input_text_normalized": input_text_normalized,
            "operator_readable_summary": operator_readable_summary,
            "error_flags_json": error_flags,
            "fallback_reason_text": fallback_reason,
            **extra,
        }
        return self.write_decision(record)

    def count_by_run(self, run_id: str) -> int:
        with self.connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM decision_log WHERE run_id = ?", (run_id,)).fetchone()
        return int(row["c"] if row else 0)

    def distinct_ticket_count(self, run_id: str) -> int:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT COUNT(DISTINCT ticket_id) AS c FROM decision_log WHERE run_id = ?", (run_id,)
            ).fetchone()
        return int(row["c"] if row else 0)

    def reconcile(self, run_id: str, expected_processed: int) -> ReconcileResult:
        logged = self.count_by_run(run_id)
        distinct = self.distinct_ticket_count(run_id)
        ok = logged == expected_processed
        message = "OK" if ok else "MISMATCH"
        return ReconcileResult(
            ok=ok,
            run_id=run_id,
            expected_processed=expected_processed,
            logged_count=logged,
            distinct_ticket_count=distinct,
            message=message,
        )

    def fetch_by_run(self, run_id: str) -> List[Dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM decision_log WHERE run_id = ? ORDER BY id ASC", (run_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def fetch_by_ticket_id(self, ticket_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM decision_log WHERE ticket_id = ? ORDER BY id DESC LIMIT ?",
                (ticket_id, int(limit)),
            ).fetchall()
        return [dict(r) for r in rows]

    def fetch_latest_by_ticket_id(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        rows = self.fetch_by_ticket_id(ticket_id, limit=1)
        return rows[0] if rows else None

    def fetch_by_id(self, row_id: int) -> Optional[Dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM decision_log WHERE id = ?", (int(row_id),)).fetchone()
        return dict(row) if row else None

    def metrics_summary(self) -> Dict[str, Any]:
        with self.connection() as conn:
            total = conn.execute("SELECT COUNT(*) AS c FROM decision_log").fetchone()["c"]
            by_action_rows = conn.execute(
                "SELECT final_action, COUNT(*) AS c FROM decision_log GROUP BY final_action"
            ).fetchall()
            guardrail_rows = conn.execute(
                "SELECT guardrail_action, COUNT(*) AS c FROM decision_log GROUP BY guardrail_action"
            ).fetchall()
        by_action = {str(r["final_action"]): int(r["c"]) for r in by_action_rows}
        by_guardrail = {str(r["guardrail_action"]): int(r["c"]) for r in guardrail_rows}
        return {
            "decisions_logged": int(total),
            "by_terminal_state": by_action,
            "guardrail_actions": by_guardrail,
        }


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m src.store.decision_log", description="Decision log store utilities")
    p.add_argument("--db", dest="db_path", default=None, help="Path to SQLite decision log DB")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Create/initialize decision log schema")

    rec = sub.add_parser("reconcile", help="Check that processed ticket count equals logged decisions")
    rec.add_argument("--run-id", required=True)
    rec.add_argument("--expected", required=True, type=int, help="Expected processed ticket count")

    demo = sub.add_parser("demo-run", help="Write 20 sample records (incl. 3 failures logged via finally)")
    demo.add_argument("--run-id", default="demo-run")

    return p


def _run_demo(store: DecisionLogStore, run_id: str) -> int:
    """Demonstration: process 20 sample tickets; 3 failures still logged in finally."""
    for i in range(1, 21):
        ticket_id = f"SAMPLE-{i:03d}"
        final_action = "answered"
        route_decision = "auto_answer"
        reason = "Demo successful processing"
        error: Optional[BaseException] = None
        try:
            if i in {5, 12, 19}:
                raise RuntimeError(f"simulated failure for {ticket_id}")
            # simulate success path
        except Exception as e:
            final_action = "failed_safe"
            route_decision = "fallback"
            reason = "Processing failed; logged in finally"
            error = e
        finally:
            store.log_terminal_outcome(
                run_id=run_id,
                ticket_id=ticket_id,
                channel=["email", "chat", "docs_comment", "forum"][i % 4],
                final_action=final_action,
                route_decision=route_decision,
                route_reason_text=reason,
                input_text_raw=f"sample body {i}",
                input_text_normalized=f"sample body {i}",
                predicted_intent="demo_intent",
                predicted_urgency="medium",
                overall_confidence=0.5 if error else 0.9,
                operator_readable_summary=f"{ticket_id}: {final_action}",
                error=error,
                guardrail_checks_json=[{"name": "pii", "passed": True}, {"name": "groundedness", "passed": True}],
                guardrail_action="none",
                guardrail_reason_text="demo checks recorded",
                prompt_versions_json={"P-CLS-001": "v1.0.0"},
                model_provider="simulation",
                model_name="demo",
                latency_ms_total=10,
            )
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    config = get_config()
    configure_logging(level=config.runtime.log_level, log_format=config.runtime.log_format)
    store = DecisionLogStore(db_path=args.db_path)

    if args.command == "init":
        print(f"OK: initialized decision log at {store.db_path}")
        return 0
    if args.command == "reconcile":
        result = store.reconcile(args.run_id, args.expected)
        status = "OK" if result.ok else "FAIL"
        print(
            f"{status}: run_id={result.run_id} expected={result.expected_processed} "
            f"logged={result.logged_count} distinct_tickets={result.distinct_ticket_count}"
        )
        return 0 if result.ok else 1
    if args.command == "demo-run":
        _run_demo(store, args.run_id)
        print(f"OK: wrote demo decisions for run_id={args.run_id} at {store.db_path}")
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
