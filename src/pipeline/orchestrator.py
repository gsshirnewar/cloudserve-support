"""Pipeline orchestration with per-node wrapped failures and terminal logging (T23)."""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from src.config import AppConfig, get_config
from src.generate import ResponseGenerator
from src.ingest.normalize import normalize_ticket
from src.logging_config import get_logger
from src.route.router import route_ticket
from src.schemas import Answer, Classification, RetrievalResult, RouteDecision, ValidationResult
from src.store.decision_log import DecisionLogStore
from src.validate import build_blocked_escalation_answer, validate_before_release

logger = get_logger(__name__)

TerminalState = str  # "answered" | "escalated" | "blocked"


@dataclass
class KillSwitch:
    enabled: bool = False
    reason: str = "kill_switch_not_enabled"

    def activate(self, reason: str = "kill_switch_activated") -> None:
        self.enabled = True
        self.reason = reason

    def deactivate(self) -> None:
        self.enabled = False
        self.reason = "kill_switch_not_enabled"


@dataclass
class PipelineResult:
    ticket_id: str
    terminal_state: TerminalState
    answer: Optional[Answer] = None
    escalation: Optional[Answer] = None
    classification: Optional[Classification] = None
    retrieval: Optional[RetrievalResult] = None
    route: Optional[RouteDecision] = None
    validation: Optional[ValidationResult] = None
    decision_row_id: Optional[int] = None
    run_id: Optional[str] = None
    errors: List[Dict[str, Any]] = field(default_factory=list)
    degraded: bool = False
    node_outcomes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        def dump(x: Any) -> Any:
            if x is None:
                return None
            if hasattr(x, "model_dump"):
                return x.model_dump(mode="json")
            if isinstance(x, dict):
                return x
            return str(x)
        return {
            "ticket_id": self.ticket_id,
            "terminal_state": self.terminal_state,
            "answer": dump(self.answer),
            "escalation": dump(self.escalation),
            "classification": dump(self.classification),
            "retrieval": dump(self.retrieval),
            "route": dump(self.route),
            "validation": dump(self.validation),
            "decision_row_id": self.decision_row_id,
            "run_id": self.run_id,
            "errors": self.errors,
            "degraded": self.degraded,
            "node_outcomes": self.node_outcomes,
        }


def _safe_ticket_id(raw: Any) -> str:
    if isinstance(raw, dict):
        v = raw.get("ticket_id") or raw.get("id")
        if v:
            return str(v)
    return f"UNKNOWN-{uuid.uuid4().hex[:8]}"


class PipelineOrchestrator:
    def __init__(
        self,
        config: Optional[AppConfig] = None,
        classifier: Any = None,
        retriever: Any = None,
        generator: Optional[ResponseGenerator] = None,
        validator: Optional[Callable[..., ValidationResult]] = None,
        store: Optional[DecisionLogStore] = None,
        llm_provider: Any = None,
        kill_switch: Optional[KillSwitch] = None,
    ):
        self.config = config or get_config()
        self.classifier = classifier
        self.retriever = retriever
        self.llm_provider = llm_provider
        self.generator = generator
        self.validator_fn = validator or validate_before_release
        self.store = store or DecisionLogStore(db_path=self.config.paths.decision_log_db_path)
        self.kill_switch = kill_switch or KillSwitch()
        self._components_lock = threading.RLock()

    def _get_classifier(self):
        with self._components_lock:
            if self.classifier is not None:
                return self.classifier
            try:
                from src.classify import TicketClassifier
                self.classifier = TicketClassifier(provider=self.llm_provider)
            except Exception as e:
                logger.warning("Classifier unavailable; using fallback-only behavior", extra={"error": str(e)})
                self.classifier = None
            return self.classifier

    def _get_retriever(self):
        with self._components_lock:
            if self.retriever is not None:
                return self.retriever
            try:
                from src.retrieve import RetrievalIndex
                idx = RetrievalIndex()
                opened = False
                try:
                    if hasattr(idx, "open"):
                        idx.open()
                        opened = True
                except Exception:
                    opened = False
                if not opened:
                    try:
                        if self.config.paths.data_dir.joinpath("documentation.json").exists() and hasattr(idx, "build"):
                            idx.build()
                            opened = True
                    except Exception:
                        opened = False
                self.retriever = idx
            except Exception as e:
                logger.warning("Retriever unavailable", extra={"error": str(e)})
                self.retriever = None
            return self.retriever

    def _get_generator(self):
        with self._components_lock:
            if self.generator is not None:
                return self.generator
            self.generator = ResponseGenerator(provider=self.llm_provider)
            return self.generator

    def _node_ingest(self, state: Dict[str, Any]) -> Dict[str, Any]:
        raw = state["raw_ticket"]
        norm = normalize_ticket(raw, index=state.get("index"))
        tdict = norm.model_dump(mode="json") if hasattr(norm, "model_dump") else dict(norm)
        tdict.setdefault("ticket_id", norm.ticket_id)
        tdict.setdefault("channel", norm.channel.value if hasattr(norm.channel, "value") else str(norm.channel))
        tdict.setdefault("subject", norm.subject)
        tdict.setdefault("body", norm.body)
        tdict.setdefault("combined_text", norm.raw_text or norm.body or "")
        state["ticket"] = tdict
        state["ticket_id"] = norm.ticket_id
        state["channel"] = tdict.get("channel") or "unknown"
        state["node_outcomes"]["ingest"] = {"ok": True, "warnings": list(getattr(norm, "ingest_warnings", []) or [])}
        return state

    def _node_classify(self, state: Dict[str, Any]) -> Dict[str, Any]:
        ticket = state["ticket"]
        clf = self._get_classifier()
        if clf is None:
            classification = Classification(
                ticket_id=str(ticket.get("ticket_id")),
                intent="unknown_intent", urgency="unknown_urgency",
                intent_confidence=0.0, urgency_confidence=0.0, overall_confidence=0.0,
                fallback_used=True, fallback_reason="classifier_unavailable",
                uncertainty_flags=["classification_fallback", "classifier_unavailable"],
                prompt_version="P-CLS-001@v1.0.0",
            )
        else:
            classification = clf.classify_ticket(ticket)
        state["classification"] = classification
        fallback_used = bool(getattr(classification, "fallback_used", False))
        if fallback_used:
            state["degraded"] = True
        state["node_outcomes"]["classify"] = {
            "ok": not fallback_used,
            "fallback_used": fallback_used,
            "intent": getattr(classification, "intent", None),
        }
        return state

    def _node_retrieve(self, state: Dict[str, Any]) -> Dict[str, Any]:
        ticket = state["ticket"]
        ticket_id = state["ticket_id"]
        retriever = self._get_retriever()
        query = " ".join([str(ticket.get("subject") or ""), str(ticket.get("body") or ticket.get("combined_text") or "")]).strip()
        if retriever is None:
            ret_obj = RetrievalResult(ticket_id=ticket_id, query=query, hits=[], top_score=None, sufficient_evidence=False, error="retriever_unavailable")
        else:
            try:
                if hasattr(retriever, "search"):
                    try:
                        result = retriever.search(query=query or ticket_id, ticket=ticket, top_k=5)
                    except TypeError:
                        try:
                            result = retriever.search(query or ticket_id, 5)
                        except TypeError:
                            result = retriever.search(query or ticket_id)
                elif hasattr(retriever, "query"):
                    result = retriever.query(query or ticket_id, top_k=5)
                elif hasattr(retriever, "retrieve"):
                    result = retriever.retrieve(query or ticket_id, ticket=ticket)
                else:
                    raise AttributeError("retriever has no search/query/retrieve method")

                if isinstance(result, RetrievalResult):
                    ret_obj = result
                elif isinstance(result, dict) and "hits" in result:
                    ret_obj = RetrievalResult.model_validate({**result, "ticket_id": ticket_id, "query": query})
                else:
                    from src.schemas import RetrievedChunk as SchemaRetrievedChunk
                    hits = []
                    for i, h in enumerate(result or []):
                        hd = h if isinstance(h, dict) else (h.model_dump() if hasattr(h, "model_dump") else getattr(h, "__dict__", {}))
                        doc_id = str(hd.get("doc_id") or "DOC-UNKNOWN")
                        chunk_id = str(hd.get("chunk_id") or f"{doc_id}#chunk_{i}")
                        hits.append(SchemaRetrievedChunk(chunk_id=chunk_id, doc_id=doc_id, title=hd.get("title"), text=str(hd.get("text") or hd.get("content") or ""), score=float(hd.get("score") or 0.0), metadata=hd.get("metadata") or {}))
                    top = hits[0].score if hits else None
                    threshold = float(self.config.thresholds.retrieval_relevance_threshold)
                    sufficient = bool(hits) and (top is not None and top >= threshold)
                    ret_obj = RetrievalResult(ticket_id=ticket_id, query=query, hits=hits, top_score=top, sufficient_evidence=sufficient, relevance_threshold=threshold)
            except Exception as e:
                ret_obj = RetrievalResult(ticket_id=ticket_id, query=query, hits=[], top_score=None, sufficient_evidence=False, error=f"{type(e).__name__}: {e}")
        state["retrieval"] = ret_obj
        state["node_outcomes"]["retrieve"] = {"ok": ret_obj.error is None, "hits": len(ret_obj.hits or []), "sufficient": bool(ret_obj.sufficient_evidence), "error": ret_obj.error}
        if ret_obj.error is not None:
            state["degraded"] = True
        return state

    def _node_route(self, state: Dict[str, Any]) -> Dict[str, Any]:
        ticket = state["ticket"]
        classification = state.get("classification")
        retrieval = state.get("retrieval")
        if self.kill_switch.enabled:
            route = RouteDecision(
                ticket_id=state["ticket_id"], route="block",
                reason=f"kill_switch_active:{self.kill_switch.reason}",
                deterministic_inputs={"kill_switch": True, "action": "block", "target": "human_review"},
                thresholds_applied={}, policy_flags=["kill_switch_active"],
                retrieved_source_ids=[h.chunk_id for h in ((retrieval.hits if retrieval else []) or [])],
                uncertainty=["kill_switch_active"],
            )
        else:
            route = route_ticket(ticket, classification, retrieval, config=self.config)
        state["route"] = route
        state["node_outcomes"]["route"] = {"ok": True, "route": route.route, "reason": route.reason}
        return state

    def _node_generate_or_escalate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        ticket = state["ticket"]
        classification = state.get("classification")
        retrieval = state.get("retrieval")
        route = state.get("route")
        generator = self._get_generator()
        attempted_actions = ["ingest", "classify", "retrieve", "route"]
        # Mode-aware generation: generator enforces evidence/policy and produces escalation/abstain as needed.
        try:
            ans = generator.generate(
                ticket=ticket,
                classification=classification,
                retrieval=retrieval,
                route=route,
                attempted_actions=attempted_actions,
            )
        except TypeError:
            # Backward/alternate signature fallback
            if route and route.route in {"escalate", "block"}:
                ans = generator.generate_escalation_summary(ticket, classification, route, retrieval, attempted_actions=attempted_actions)
            else:
                ans = generator.generate(ticket, classification, retrieval, route)
        state["answer"] = ans
        state["generated_path"] = "escalate" if (route and route.route in {"escalate", "block"}) else "generate"
        state["node_outcomes"]["generate"] = {"ok": True, "action": getattr(ans, "action", None), "path": state.get("generated_path")}
        return state

    def _node_validate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        answer = state.get("answer")
        if answer is None:
            vr = ValidationResult(ticket_id=state["ticket_id"], passed=False, blocked=True, action="escalate", checks=[], findings=[{"check": "pipeline", "type": "missing_answer", "detail": "No answer produced"}], pii_detected=False, unsupported_claims_detected=False, validator_version="validator@t22-v1")
        else:
            vr = self.validator_fn(answer=answer, ticket=state.get("ticket"), classification=state.get("classification"), retrieval=state.get("retrieval"), route=state.get("route"))
        state["validation"] = vr
        if vr.blocked or not vr.passed:
            state["escalation"] = build_blocked_escalation_answer(state["ticket_id"], vr, base_answer=answer)
            state["released_answer"] = None
            state["terminal_state"] = "blocked"
        else:
            state["released_answer"] = answer
            if answer and answer.action in {"answer", "assist_draft"}:
                state["terminal_state"] = "answered"
                state["escalation"] = None
            elif answer and answer.action == "abstain":
                state["terminal_state"] = "escalated"
                state["escalation"] = answer
            else:
                state["terminal_state"] = "escalated"
                state["escalation"] = answer
        state["node_outcomes"]["validate"] = {"ok": True, "passed": vr.passed, "blocked": vr.blocked, "action": vr.action}
        return state

    def _wrap_node(self, name: str, fn: Callable[[Dict[str, Any]], Dict[str, Any]], state: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return fn(state)
        except Exception as e:
            logger.exception("Pipeline node failed", extra={"node": name, "ticket_id": state.get("ticket_id")})
            state.setdefault("errors", []).append({"node": name, "type": type(e).__name__, "message": str(e)})
            state["degraded"] = True
            state.setdefault("node_outcomes", {})[name] = {"ok": False, "error": f"{type(e).__name__}: {e}"}
            tid = state.get("ticket_id") or _safe_ticket_id(state.get("raw_ticket"))
            if name == "ingest":
                raw = state.get("raw_ticket") or {}
                body = raw.get("body") if isinstance(raw, dict) else str(raw)
                body_s = "" if body is None else str(body)
                state["ticket"] = {"ticket_id": tid, "channel": "unknown", "subject": raw.get("subject") if isinstance(raw, dict) else None, "body": body_s, "combined_text": body_s}
                state["ticket_id"] = tid
                state["channel"] = raw.get("channel", "unknown") if isinstance(raw, dict) else "unknown"
            elif name == "classify" and state.get("classification") is None:
                state["classification"] = Classification(ticket_id=tid, intent="unknown_intent", urgency="unknown_urgency", intent_confidence=0.0, urgency_confidence=0.0, overall_confidence=0.0, fallback_used=True, fallback_reason=f"node_error:{type(e).__name__}", uncertainty_flags=["classification_fallback", "node_error"], prompt_version="P-CLS-001@v1.0.0")
            elif name == "retrieve" and state.get("retrieval") is None:
                state["retrieval"] = RetrievalResult(ticket_id=tid, query="", hits=[], top_score=None, sufficient_evidence=False, error=f"node_error:{type(e).__name__}")
            elif name == "route" and state.get("route") is None:
                state["route"] = RouteDecision(ticket_id=tid, route="escalate", reason=f"routing_failed:{type(e).__name__}", deterministic_inputs={"error": type(e).__name__}, thresholds_applied={}, policy_flags=["node_error"], retrieved_source_ids=[], uncertainty=["node_error"])
            elif name == "generate" and state.get("answer") is None:
                state["answer"] = Answer(ticket_id=tid, action="escalate_recommendation", answer_text="Processing error occurred; escalating safely.", claims=[], citations=[], confidence=0.0, unknown_or_insufficient_evidence=True, raw_output={"error": str(e)})
            elif name == "validate" and state.get("validation") is None:
                vr = ValidationResult(ticket_id=tid, passed=False, blocked=True, action="escalate", checks=[], findings=[{"check": "validate", "type": "validator_error", "detail": str(e)}], pii_detected=False, unsupported_claims_detected=False, validator_version="validator@t22-v1")
                state["validation"] = vr
                state["terminal_state"] = "blocked"
                state["escalation"] = build_blocked_escalation_answer(tid, vr, base_answer=state.get("answer"))
            return state

    def process_ticket(self, raw_ticket: Any, run_id: Optional[str] = None, index: Optional[int] = None) -> PipelineResult:
        started = time.perf_counter()
        run_id = run_id or f"run-{uuid.uuid4().hex[:12]}"
        ticket_id_hint = _safe_ticket_id(raw_ticket)
        state: Dict[str, Any] = {"raw_ticket": raw_ticket if isinstance(raw_ticket, dict) else {"value": raw_ticket, "ticket_id": ticket_id_hint}, "index": index, "run_id": run_id, "ticket_id": ticket_id_hint, "errors": [], "degraded": False, "node_outcomes": {}}
        try:
            self._wrap_node("ingest", self._node_ingest, state)
            self._wrap_node("classify", self._node_classify, state)
            self._wrap_node("retrieve", self._node_retrieve, state)
            self._wrap_node("route", self._node_route, state)
            self._wrap_node("generate", self._node_generate_or_escalate, state)
            self._wrap_node("validate", self._node_validate, state)  # always-on
            if not state.get("terminal_state"):
                state["terminal_state"] = "escalated"
        except Exception as e:
            state.setdefault("errors", []).append({"node": "pipeline", "type": type(e).__name__, "message": str(e)})
            state["degraded"] = True
            state["terminal_state"] = "escalated"
        finally:
            decision_row_id = self._log_terminal(state, run_id=run_id, latency_ms=int((time.perf_counter() - started) * 1000))

        terminal = state.get("terminal_state") or "escalated"
        if terminal not in {"answered", "escalated", "blocked"}:
            terminal = "escalated"
        escalation = state.get("escalation")
        if terminal == "blocked" and escalation is None and state.get("validation"):
            escalation = build_blocked_escalation_answer(state.get("ticket_id", ticket_id_hint), state["validation"], base_answer=state.get("answer"))
        return PipelineResult(
            ticket_id=str(state.get("ticket_id") or ticket_id_hint),
            terminal_state=terminal,
            answer=state.get("released_answer") or state.get("answer"),
            escalation=escalation,
            classification=state.get("classification"),
            retrieval=state.get("retrieval"),
            route=state.get("route"),
            validation=state.get("validation"),
            decision_row_id=decision_row_id,
            run_id=run_id,
            errors=list(state.get("errors") or []),
            degraded=bool(state.get("degraded") or state.get("errors")),
            node_outcomes=dict(state.get("node_outcomes") or {}),
        )

    def process_tickets(self, tickets: Sequence[Any], run_id: Optional[str] = None) -> Tuple[List[PipelineResult], str]:
        run_id = run_id or f"run-{uuid.uuid4().hex[:12]}"
        results: List[PipelineResult] = []
        for i, t in enumerate(tickets):
            try:
                results.append(self.process_ticket(t, run_id=run_id, index=i))
            except Exception as e:
                tid = _safe_ticket_id(t)
                logger.exception("Unhandled ticket processing error", extra={"ticket_id": tid})
                try:
                    row = self.store.log_terminal_outcome(run_id=run_id, ticket_id=tid, channel="unknown", final_action="escalated", route_decision="fallback", route_reason_text="unhandled_pipeline_exception", operator_readable_summary=f"{tid}: escalated (unhandled exception)", error=e)
                except Exception:
                    row = None
                results.append(PipelineResult(ticket_id=tid, terminal_state="escalated", decision_row_id=row, run_id=run_id, errors=[{"node": "pipeline", "type": type(e).__name__, "message": str(e)}], degraded=True))
        return results, run_id

    def _log_terminal(self, state: Dict[str, Any], run_id: str, latency_ms: int) -> Optional[int]:
        ticket = state.get("ticket") or {}
        ticket_id = str(state.get("ticket_id") or _safe_ticket_id(state.get("raw_ticket")))
        channel = str(state.get("channel") or ticket.get("channel") or "unknown")
        classification = state.get("classification")
        retrieval = state.get("retrieval")
        route = state.get("route")
        answer = state.get("released_answer") or state.get("answer")
        validation = state.get("validation")
        terminal = state.get("terminal_state") or "escalated"
        if terminal not in {"answered", "escalated", "blocked"}:
            terminal = "escalated"
        hits = (retrieval.hits or []) if retrieval else []
        guardrail_checks = [c.model_dump(mode="json") if hasattr(c, "model_dump") else c for c in (getattr(validation, "checks", []) or [])] if validation else []
        failed_checks = [c.get("name") for c in guardrail_checks if isinstance(c, dict) and not c.get("passed", True)]
        escalation_payload = None
        if terminal in {"escalated", "blocked"}:
            esc = state.get("escalation") or (answer if answer and getattr(answer, "action", None) in {"escalate_recommendation", "abstain"} else None)
            escalation_payload = esc.model_dump(mode="json") if esc and hasattr(esc, "model_dump") else esc
        raw_text = str(ticket.get("raw_text") or ticket.get("body") or ticket.get("combined_text") or "")
        record = {
            "run_id": run_id, "ticket_id": ticket_id, "channel": channel,
            "final_action": terminal,
            "route_decision": getattr(route, "route", "fallback") if route else "fallback",
            "threshold_used": float(((getattr(route, "thresholds_applied", {}) or {}).get("route_auto_min_confidence")) or 0.0) if route else 0.0,
            "route_reason_text": getattr(route, "reason", "pipeline_fallback") if route else "pipeline_fallback",
            "predicted_intent": getattr(classification, "intent", "unknown_fallback") if classification else "unknown_fallback",
            "predicted_urgency": getattr(classification, "urgency", "unknown_fallback") if classification else "unknown_fallback",
            "intent_confidence": float(getattr(classification, "intent_confidence", 0.0) or 0.0) if classification else 0.0,
            "urgency_confidence": float(getattr(classification, "urgency_confidence", 0.0) or 0.0) if classification else 0.0,
            "overall_confidence": float(getattr(classification, "overall_confidence", 0.0) or 0.0) if classification else 0.0,
            "confidence_method": "model+fallback" if classification else "not_set",
            "classification_alternatives_json": {"intent": [a.model_dump(mode="json") for a in (getattr(classification, "intent_alternatives", []) or [])] if classification else [], "urgency": [a.model_dump(mode="json") for a in (getattr(classification, "urgency_alternatives", []) or [])] if classification else []},
            "retrieval_query": getattr(retrieval, "query", "") if retrieval else "",
            "retrieval_results_json": [h.model_dump(mode="json") if hasattr(h, "model_dump") else h for h in hits],
            "retrieved_source_ids_json": [getattr(h, "chunk_id", None) or getattr(h, "doc_id", None) for h in hits],
            "retrieved_passages_json": [{"chunk_id": getattr(h, "chunk_id", None), "doc_id": getattr(h, "doc_id", None), "score": getattr(h, "score", None)} for h in hits],
            "citation_ids_json": [c.model_dump(mode="json") if hasattr(c, "model_dump") else c for c in (getattr(answer, "citations", []) or [])] if answer else [],
            "generated_answer_draft": getattr(answer, "answer_text", None) if answer and getattr(answer, "action", None) == "assist_draft" else None,
            "generated_answer_final": getattr(answer, "answer_text", None) if answer and terminal == "answered" else None,
            "response_sent": 1 if terminal == "answered" else 0,
            "guardrail_checks_json": guardrail_checks,
            "guardrail_action": "blocked_escalated" if failed_checks else ("passed" if validation and getattr(validation, "passed", False) else "none"),
            "guardrail_reason_text": "; ".join([str(x) for x in failed_checks]) if failed_checks else ("ok" if validation else "not_run"),
            "escalation_payload_json": escalation_payload,
            "fallback_reason_text": getattr(classification, "fallback_reason", None) if classification else None,
            "error_flags_json": list(state.get("errors") or []),
            "operator_readable_summary": f"{ticket_id}: {terminal} ({getattr(route, 'reason', 'n/a') if route else 'n/a'})",
            "model_provider": getattr(self.config.provider, "llm_provider", "n/a"),
            "model_name": getattr(answer, "model_name", None) or getattr(self.config.provider, "openrouter_model", "n/a"),
            "prompt_versions_json": {"P-CLS-001": getattr(classification, "prompt_version", None) if classification else None, "generator": getattr(answer, "prompt_version", None) if answer else None, "validator": getattr(validation, "validator_version", None) if validation else None},
            "latency_ms_total": int(latency_ms),
            "latency_breakdown_json": {},
            "input_text_raw": raw_text,
            "input_text_normalized": raw_text,
            "input_metadata_json": {
                "channel": channel,
                "run_id": run_id,
                "input_index": state.get("index"),
                "node_outcomes": state.get("node_outcomes", {}),
            },
        }
        try:
            return self.store.write_decision(record)
        except Exception as e:
            logger.exception("Failed to write terminal decision log", extra={"ticket_id": ticket_id})
            try:
                return self.store.log_terminal_outcome(run_id=run_id, ticket_id=ticket_id, channel=channel, final_action=terminal, route_decision=getattr(route, "route", "fallback") if route else "fallback", route_reason_text="log_fallback", input_text_raw=raw_text, input_text_normalized=raw_text, operator_readable_summary=f"{ticket_id}: {terminal}", error=e)
            except Exception:
                return None
