"""Deterministic decision routing policy (T20, no LLM)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from src.config import AppConfig, get_config
from src.schemas import Classification, RetrievalResult, RouteDecision


# Sensitive/prohibited intents derived from T05/Stage 1 constraints (deterministic policy).
DEFAULT_PROHIBITED_AUTO_INTENTS = {
    "security_incident",
    "compliance_request",
    "data_residency",
    "data_export",  # may include sensitive/restricted handling in some contexts
}


@dataclass(frozen=True)
class RoutingPolicy:
    route_auto_min_confidence: float = 0.85
    route_assist_min_confidence: float = 0.60
    require_sufficient_evidence_for_auto: bool = True
    prohibited_auto_intents: frozenset[str] = field(
        default_factory=lambda: frozenset(DEFAULT_PROHIBITED_AUTO_INTENTS)
    )
    block_on_must_not_auto: bool = True
    block_on_no_evidence: bool = True

    @classmethod
    def from_config(cls, config: Optional[AppConfig] = None) -> "RoutingPolicy":
        cfg = config or get_config()
        return cls(
            route_auto_min_confidence=float(cfg.thresholds.route_auto_min_confidence),
            route_assist_min_confidence=float(cfg.thresholds.route_assist_min_confidence),
        )


def _to_mapping(ticket: Any) -> Mapping[str, Any]:
    if ticket is None:
        return {}
    if isinstance(ticket, Mapping):
        return ticket
    if hasattr(ticket, "model_dump"):
        try:
            return ticket.model_dump()  # type: ignore[attr-defined]
        except Exception:
            pass
    if hasattr(ticket, "dict"):
        try:
            return ticket.dict()  # type: ignore[attr-defined]
        except Exception:
            pass
    return {}


def _get_ticket_id(ticket: Any, classification: Optional[Classification], retrieval: Optional[RetrievalResult]) -> str:
    t = _to_mapping(ticket)
    for candidate in (t.get("ticket_id"), getattr(ticket, "ticket_id", None), classification.ticket_id if classification else None, retrieval.ticket_id if retrieval else None):
        if candidate:
            return str(candidate)
    return "UNKNOWN_TICKET"


def _is_must_not_auto(ticket: Mapping[str, Any]) -> tuple[bool, List[str]]:
    flags: List[str] = []
    must = False
    # explicit fields/metadata
    for key in ("must_not_auto_respond", "must_not_auto", "prohibit_auto"):
        if bool(ticket.get(key)) is True:
            must = True
            flags.append(key)
    meta = ticket.get("metadata") or {}
    if isinstance(meta, Mapping):
        for key in ("must_not_auto_respond", "must_not_auto", "prohibit_auto"):
            if bool(meta.get(key)) is True:
                must = True
                flags.append(f"metadata.{key}")
    labels = ticket.get("labels") or {}
    if isinstance(labels, Mapping) and bool(labels.get("must_not_auto_respond")) is True:
        must = True
        flags.append("labels.must_not_auto_respond")
    policy_flags = ticket.get("policy_flags") or []
    if isinstance(policy_flags, (list, tuple, set)):
        for pf in policy_flags:
            pf_s = str(pf).lower()
            if "must_not_auto" in pf_s or "no_auto" in pf_s or "prohibit_auto" in pf_s:
                must = True
                flags.append(f"policy_flag:{pf}")
    return must, flags


def _has_sufficient_evidence(retrieval: Optional[RetrievalResult]) -> bool:
    if retrieval is None:
        return False
    if retrieval.error:
        return False
    if retrieval.sufficient_evidence:
        return True
    hits = retrieval.hits or []
    return len(hits) > 0 and retrieval.sufficient_evidence is True


def route_ticket(
    ticket: Any,
    classification: Optional[Classification],
    retrieval: Optional[RetrievalResult],
    *,
    policy: Optional[RoutingPolicy] = None,
    config: Optional[AppConfig] = None,
) -> RouteDecision:
    """Pure deterministic routing function (no LLM, no I/O, no randomness)."""
    cfg = config or get_config()
    pol = policy or RoutingPolicy.from_config(cfg)
    t = _to_mapping(ticket)
    ticket_id = _get_ticket_id(ticket, classification, retrieval)

    intent = (classification.intent if classification else None) or "unknown_intent"
    urgency = (classification.urgency if classification else None) or "unknown_urgency"
    conf = float(classification.overall_confidence) if classification else 0.0
    fallback_used = bool(classification.fallback_used) if classification else True
    uncertainty = list((classification.uncertainty_flags if classification else []) or [])
    if classification is None:
        uncertainty.append("missing_classification")
    if retrieval is None:
        uncertainty.append("missing_retrieval")

    sufficient = _has_sufficient_evidence(retrieval)
    top_score = retrieval.top_score if retrieval else None
    retrieved_ids = [h.doc_id for h in (retrieval.hits or [])] if retrieval else []
    # stable unique doc IDs in rank order
    seen = set()
    retrieved_source_ids = []
    for did in retrieved_ids:
        if did not in seen:
            retrieved_source_ids.append(did)
            seen.add(did)

    must_not_auto, must_flags = _is_must_not_auto(t)
    answerable = t.get("answerable_from_docs")
    if answerable is None and isinstance(t.get("labels"), Mapping):
        answerable = t["labels"].get("answerable_from_docs")

    thresholds_applied: Dict[str, Any] = {
        "route_auto_min_confidence": pol.route_auto_min_confidence,
        "route_assist_min_confidence": pol.route_assist_min_confidence,
        "require_sufficient_evidence_for_auto": pol.require_sufficient_evidence_for_auto,
        "block_on_must_not_auto": pol.block_on_must_not_auto,
        "block_on_no_evidence": pol.block_on_no_evidence,
        "retrieval_relevance_threshold": float(cfg.thresholds.retrieval_relevance_threshold),
    }

    deterministic_inputs: Dict[str, Any] = {
        "ticket_id": ticket_id,
        "intent": intent,
        "urgency": urgency,
        "overall_confidence": conf,
        "classification_fallback_used": fallback_used,
        "sufficient_evidence": bool(sufficient),
        "retrieval_hit_count": len(retrieval.hits) if retrieval and retrieval.hits else 0,
        "retrieval_top_score": top_score,
        "retrieval_error": retrieval.error if retrieval else "missing_retrieval",
        "must_not_auto": bool(must_not_auto),
        "answerable_from_docs": answerable,
    }

    policy_flags: List[str] = []

    # 1) Prohibited / must-not-auto
    if intent in pol.prohibited_auto_intents:
        policy_flags.append(f"prohibited_intent:{intent}")
    if must_not_auto:
        policy_flags.extend(must_flags)
    if intent in pol.prohibited_auto_intents or must_not_auto:
        action = "block" if pol.block_on_must_not_auto else "escalate"
        target = "human_review_queue" if action == "escalate" else "blocked_no_auto"
        reason = (
            f"Blocked/escalated: auto-response prohibited (intent={intent}, must_not_auto={must_not_auto}). "
            f"Target={target}."
        )
        deterministic_inputs.update({"action": action, "target": target})
        return RouteDecision(
            ticket_id=ticket_id,
            route=action,  # type: ignore[arg-type]
            reason=reason,
            deterministic_inputs=deterministic_inputs,
            thresholds_applied=thresholds_applied,
            policy_flags=policy_flags,
            escalation_summary=(
                f"Ticket {ticket_id}: prohibited/must-not-auto case (intent={intent}, urgency={urgency}, confidence={conf:.3f})."
            ) if action == "escalate" else None,
            retrieved_source_ids=retrieved_source_ids,
            uncertainty=uncertainty,
        )

    # 2) No evidence / no-doc
    if not sufficient or answerable is False:
        policy_flags.append("insufficient_evidence" if not sufficient else "not_answerable_from_docs")
        if pol.block_on_no_evidence:
            action = "block"
            target = "blocked_no_evidence"
            reason = (
                f"Blocked: insufficient/no-doc evidence for safe auto response "
                f"(sufficient_evidence={sufficient}, answerable_from_docs={answerable}, top_score={top_score}). Target={target}."
            )
        else:
            action = "escalate"
            target = "human_support_queue"
            reason = (
                f"Escalated: insufficient/no-doc evidence "
                f"(sufficient_evidence={sufficient}, answerable_from_docs={answerable}). Target={target}."
            )
        deterministic_inputs.update({"action": action, "target": target})
        return RouteDecision(
            ticket_id=ticket_id,
            route=action,  # type: ignore[arg-type]
            reason=reason,
            deterministic_inputs=deterministic_inputs,
            thresholds_applied=thresholds_applied,
            policy_flags=policy_flags,
            escalation_summary=f"Ticket {ticket_id}: no sufficient evidence for grounded response; escalate/block.",
            retrieved_source_ids=retrieved_source_ids,
            uncertainty=uncertainty,
        )

    # 3) Classification uncertainty/fallback or low confidence
    if fallback_used or intent in {"unknown_intent", "unknown", ""} or urgency in {"unknown_urgency", "unknown", ""}:
        policy_flags.append("classification_fallback_or_unknown")
        action = "escalate"
        target = "human_support_queue"
        reason = (
            f"Escalated: classification fallback/unknown (intent={intent}, urgency={urgency}, confidence={conf:.3f}). Target={target}."
        )
        deterministic_inputs.update({"action": action, "target": target})
        return RouteDecision(
            ticket_id=ticket_id,
            route=action,  # type: ignore[arg-type]
            reason=reason,
            deterministic_inputs=deterministic_inputs,
            thresholds_applied=thresholds_applied,
            policy_flags=policy_flags,
            escalation_summary=f"Ticket {ticket_id}: classification uncertain/fallback; human review required.",
            retrieved_source_ids=retrieved_source_ids,
            uncertainty=uncertainty,
        )

    # 4) Confidence-based routing
    if conf >= pol.route_auto_min_confidence:
        action = "auto_answer"
        target = "auto_response"
        reason = (
            f"Auto-answer: confidence {conf:.3f} >= {pol.route_auto_min_confidence:.3f} with sufficient evidence. Target={target}."
        )
    elif conf >= pol.route_assist_min_confidence:
        action = "assist_draft"
        target = "agent_assist_draft"
        reason = (
            f"Assist draft: confidence {conf:.3f} in assist band "
            f"[{pol.route_assist_min_confidence:.3f}, {pol.route_auto_min_confidence:.3f}). Target={target}."
        )
    else:
        action = "escalate"
        target = "human_support_queue"
        reason = (
            f"Escalated: confidence {conf:.3f} < {pol.route_assist_min_confidence:.3f}. Target={target}."
        )

    deterministic_inputs.update({"action": action, "target": target})
    return RouteDecision(
        ticket_id=ticket_id,
        route=action,  # type: ignore[arg-type]
        reason=reason,
        deterministic_inputs=deterministic_inputs,
        thresholds_applied=thresholds_applied,
        policy_flags=policy_flags,
        escalation_summary=(
            f"Ticket {ticket_id}: routed to {action} (intent={intent}, urgency={urgency}, confidence={conf:.3f})."
            if action == "escalate"
            else None
        ),
        retrieved_source_ids=retrieved_source_ids,
        uncertainty=uncertainty,
    )
