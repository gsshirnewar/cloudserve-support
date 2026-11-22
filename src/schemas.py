"""Pydantic schemas for tickets, pipeline outputs, and decision records (T14 skeleton)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Channel(str, Enum):
    EMAIL = "email"
    CHAT = "chat"
    DOCS_COMMENT = "docs_comment"
    FORUM = "forum"
    UNKNOWN = "unknown"


class Ticket(BaseModel):
    """Raw input ticket representation (schema-flexible)."""

    model_config = ConfigDict(extra="allow")

    ticket_id: Optional[str] = None
    channel: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    received_at: Optional[datetime] = None
    customer: Optional[Dict[str, Any]] = None
    labels: Optional[Dict[str, Any]] = None
    history: Optional[Dict[str, Any]] = None
    raw: Optional[Dict[str, Any]] = None


class NormalisedTicket(BaseModel):
    """Normalized internal ticket used across pipeline components."""

    ticket_id: str
    channel: Channel
    subject: Optional[str] = None
    body: Optional[str] = None
    raw_text: str = ""
    received_at: Optional[datetime] = None
    customer: Dict[str, Any] = Field(default_factory=dict)
    labels: Dict[str, Any] = Field(default_factory=dict)
    history: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ingest_warnings: List[str] = Field(default_factory=list)
    original: Dict[str, Any] = Field(default_factory=dict)


class AlternativePrediction(BaseModel):
    label: str
    score: float = Field(ge=0.0, le=1.0)
    reason: Optional[str] = None


class Classification(BaseModel):
    """Intent/urgency classification output with confidence and alternatives."""

    ticket_id: str
    intent: str
    urgency: str
    intent_confidence: float = Field(ge=0.0, le=1.0)
    urgency_confidence: float = Field(ge=0.0, le=1.0)
    overall_confidence: float = Field(ge=0.0, le=1.0)
    intent_alternatives: List[AlternativePrediction] = Field(default_factory=list)
    urgency_alternatives: List[AlternativePrediction] = Field(default_factory=list)
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    uncertainty_flags: List[str] = Field(default_factory=list)
    model_name: Optional[str] = None
    prompt_version: Optional[str] = None


class RetrievedChunk(BaseModel):
    chunk_id: str
    doc_id: str
    title: Optional[str] = None
    text: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    """Ranked retrieval results and sufficiency signals."""

    ticket_id: str
    query: Optional[str] = None
    hits: List[RetrievedChunk] = Field(default_factory=list)
    top_score: Optional[float] = None
    sufficient_evidence: bool = False
    relevance_threshold: Optional[float] = None
    retrieval_strategy: str = "semantic"
    error: Optional[str] = None


class RouteDecision(BaseModel):
    """Deterministic routing decision with explainable reason."""

    ticket_id: str
    route: Literal["auto_answer", "assist_draft", "escalate", "block"]
    reason: str
    deterministic_inputs: Dict[str, Any] = Field(default_factory=dict)
    thresholds_applied: Dict[str, Any] = Field(default_factory=dict)
    policy_flags: List[str] = Field(default_factory=list)
    escalation_summary: Optional[str] = None
    retrieved_source_ids: List[str] = Field(default_factory=list)
    uncertainty: List[str] = Field(default_factory=list)


class Citation(BaseModel):
    citation_id: str
    doc_id: str
    chunk_id: Optional[str] = None
    claim_id: Optional[str] = None
    quote_or_span: Optional[str] = None


class Answer(BaseModel):
    """Generated response with grounding/citation metadata."""

    ticket_id: str
    action: Literal["answer", "assist_draft", "abstain", "escalate_recommendation"] = "abstain"
    answer_text: str = ""
    claims: List[Dict[str, Any]] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    unknown_or_insufficient_evidence: bool = True
    model_name: Optional[str] = None
    prompt_version: Optional[str] = None
    raw_output: Optional[Dict[str, Any]] = None


class GuardrailCheck(BaseModel):
    name: str
    passed: bool
    severity: Literal["info", "low", "medium", "high", "critical"] = "info"
    details: Optional[str] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    """Pre-release validation/guardrail outcome."""

    ticket_id: str
    passed: bool
    blocked: bool
    action: Literal["allow", "block", "escalate", "redact_and_recheck"] = "allow"
    checks: List[GuardrailCheck] = Field(default_factory=list)
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    pii_detected: bool = False
    unsupported_claims_detected: bool = False
    validator_version: Optional[str] = None


class DecisionRecord(BaseModel):
    """Audit record for a processed ticket (A8-oriented skeleton)."""

    decision_id: str
    ticket_id: str
    channel: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    input_ref: Dict[str, Any] = Field(default_factory=dict)
    classification: Optional[Classification] = None
    retrieval: Optional[RetrievalResult] = None
    route: Optional[RouteDecision] = None
    answer: Optional[Answer] = None
    validation: Optional[ValidationResult] = None
    final_outcome: Literal[
        "answered",
        "assist_draft",
        "escalated",
        "blocked",
        "failed",
        "unknown",
    ] = "unknown"
    reason: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    sources: List[str] = Field(default_factory=list)
    prompt_versions: Dict[str, str] = Field(default_factory=dict)
    model_metadata: Dict[str, Any] = Field(default_factory=dict)
    latency_ms: Optional[float] = None
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    guardrail_activations: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
