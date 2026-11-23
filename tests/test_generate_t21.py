import json

from src.generate.generator import ResponseGenerator
from src.llm.provider import LLMProvider, SimulationBackend
from src.schemas import Classification, RetrievalResult, RetrievedChunk, RouteDecision


def _ticket():
    return {"ticket_id": "T-1", "channel": "email", "subject": "How to rotate keys", "body": "Need steps to rotate API keys."}


def _classification(conf=0.9):
    return Classification(
        ticket_id="T-1",
        intent="api_key_issue",
        urgency="medium",
        intent_confidence=conf,
        urgency_confidence=conf,
        overall_confidence=conf,
        fallback_used=False,
        prompt_version="P-CLS-001@v1.0.0",
    )


def _retrieval(sufficient=True):
    hits = [
        RetrievedChunk(
            doc_id="DOC-API-001",
            chunk_id="DOC-API-001#chunk_0",
            title="API Keys",
            text="Rotate keys by generating a new key and revoking the old one in the console.",
            score=0.82,
        )
    ] if sufficient else []
    return RetrievalResult(
        ticket_id="T-1",
        query="rotate api keys",
        hits=hits,
        top_score=0.82 if sufficient else None,
        sufficient_evidence=sufficient and bool(hits),
        relevance_threshold=0.3,
    )


def _route(route="auto_answer", reason="ok"):
    return RouteDecision(
        ticket_id="T-1",
        route=route,
        reason=reason,
        thresholds_applied={"route_auto_min_confidence": 0.85},
        deterministic_inputs={"action": route, "target": "auto"},
        policy_flags=[],
    )


def test_grounded_output_contains_citations():
    payload = {
        "prompt_id": "P-GEN-001",
        "prompt_version": "v1.0.0",
        "ticket_id": "T-1",
        "action": "answer",
        "answer_text": "You can rotate API keys by generating a new key and revoking the old key.",
        "claims": [
            {
                "claim_id": "c1",
                "text": "Generate a new key and revoke the old key.",
                "support_status": "supported",
                "citation_ids": ["DOC-API-001#chunk_0"],
            }
        ],
        "citations": [
            {"citation_id": "DOC-API-001#chunk_0", "doc_id": "DOC-API-001", "chunk_id": "DOC-API-001#chunk_0"}
        ],
        "confidence": 0.88,
        "unknown_or_insufficient_evidence": False,
        "customer_safe": True,
        "notes_for_reviewer": "grounded",
    }
    provider = LLMProvider(backend=SimulationBackend(mode="off", success_text=json.dumps(payload)))
    gen = ResponseGenerator(provider=provider)
    ans = gen.generate(_ticket(), _classification(), _retrieval(sufficient=True), _route("auto_answer"))

    assert ans.action in {"answer", "assist_draft"}
    assert ans.unknown_or_insufficient_evidence is False
    assert len(ans.citations) >= 1
    assert ans.citations[0].doc_id == "DOC-API-001"
    assert "DOC-API-001#chunk_0" in (ans.citations[0].chunk_id or ans.citations[0].citation_id)


def test_insufficient_evidence_abstains_no_fabricated_answer():
    gen = ResponseGenerator(provider=LLMProvider(backend=SimulationBackend(mode="off", success_text="{}")))
    # even if model were called, route/evidence forces safe path; here evidence insufficient
    ans = gen.generate(_ticket(), _classification(), _retrieval(sufficient=False), _route("assist_draft"))
    assert ans.action in {"abstain", "escalate_recommendation"}
    assert ans.unknown_or_insufficient_evidence is True
    assert len(ans.citations) == 0
    assert "enough" in ans.answer_text.lower() or "escalat" in ans.answer_text.lower() or "abstain" in ans.answer_text.lower() or "insufficient" in ans.answer_text.lower()


def test_escalation_route_produces_context_summary():
    esc_payload = {
        "prompt_id": "P-ESC-001",
        "prompt_version": "v1.0.0",
        "ticket_id": "T-1",
        "escalation_summary": "Ticket escalated due to policy; insufficient auto-response conditions.",
        "customer_issue": "API key rotation",
        "intent": "api_key_issue",
        "urgency": "medium",
        "confidence": 0.5,
        "why_escalated": "Policy requires human review.",
        "what_was_tried": ["ingest", "classify", "retrieve", "route"],
        "what_is_uncertain": ["Automated confidence insufficient."],
        "retrieved_sources": [{"doc_id": "DOC-API-001", "chunk_id": "DOC-API-001#chunk_0", "score": 0.82, "note": "retrieved"}],
        "recommended_next_step": "Agent should confirm steps with cited source.",
        "policy_or_safety_flags": ["manual_review"],
    }
    provider = LLMProvider(backend=SimulationBackend(mode="off", success_text=json.dumps(esc_payload)))
    gen = ResponseGenerator(provider=provider)
    ans = gen.generate(
        _ticket(),
        _classification(conf=0.5),
        _retrieval(sufficient=True),
        _route("escalate", reason="low confidence/policy"),
        attempted_actions=["ingest", "classify", "retrieve", "route"],
    )
    assert ans.action == "escalate_recommendation"
    assert ans.answer_text
    assert ans.raw_output and ans.raw_output.get("why_escalated")
    assert len(ans.citations) >= 1


def test_escalation_falls_back_deterministically_on_provider_failure():
    provider = LLMProvider(backend=SimulationBackend(mode="timeout"))
    gen = ResponseGenerator(provider=provider)
    ans = gen.generate_escalation_summary(
        _ticket(),
        _classification(conf=0.4),
        _route("escalate", reason="timeout"),
        _retrieval(sufficient=False),
        attempted_actions=["ingest", "classify", "retrieve", "route", "generate"],
        simulation_mode="timeout",
    )
    assert ans.action == "escalate_recommendation"
    assert "escalat" in ans.answer_text.lower()
    assert ans.prompt_version and "P-ESC-001" in ans.prompt_version
    assert ans.raw_output and ans.raw_output.get("why_escalated")
