import json
from pathlib import Path

from src.schemas import Answer, Citation, Classification, RetrievalResult, RetrievedChunk, RouteDecision
from src.validate import (
    GuardrailPolicy,
    ResponseValidator,
    build_blocked_escalation_answer,
    validate_before_release,
)


def _retrieval(ticket_id="T-1", doc_id="DOC-001", chunk_id="chunk-1", text="Restart the device and check Settings > Network."):
    cid = f"{doc_id}#{chunk_id}"
    return RetrievalResult(
        ticket_id=ticket_id,
        query="q",
        hits=[RetrievedChunk(doc_id=doc_id, chunk_id=cid, title="Guide", text=text, score=0.9)],
        top_score=0.9,
        sufficient_evidence=True,
        relevance_threshold=0.3,
    )


def _grounded_answer(ticket_id="T-1"):
    doc_id = "DOC-001"
    cid = f"{doc_id}#chunk-1"
    return Answer(
        ticket_id=ticket_id,
        action="answer",
        answer_text="Restart the device and check Settings > Network to restore connectivity.",
        claims=[{"text": "Restart the device and check Settings > Network.", "citations": [cid]}],
        citations=[Citation(citation_id="c1", doc_id=doc_id, chunk_id=cid, claim_id="claim-1")],
        confidence=0.8,
        unknown_or_insufficient_evidence=False,
    )


def test_pii_in_answer_blocked_and_escalation_created_with_check_logged():
    ret = _retrieval()
    ans = _grounded_answer()
    ans.answer_text = "Contact support at leaked.user@example.com or call +1 415-555-1234 with token sk-ABCDEF1234567890ABCDE."
    v = validate_before_release(ans, ticket={"ticket_id": "T-PII"}, retrieval=ret)
    assert v.passed is False
    assert v.blocked is True
    assert v.pii_detected is True
    pii = next(c for c in v.checks if c.name == "pii_scan")
    assert pii.passed is False
    assert any(f.get("check") == "pii_scan" for f in v.findings)
    esc = build_blocked_escalation_answer("T-PII", v, base_answer=ans)
    assert esc.action == "escalate_recommendation"
    assert esc.raw_output and esc.raw_output.get("blocked") is True
    assert "pii_scan" in (esc.raw_output.get("guardrail_failed_checks") or [])
    assert "leaked.user@example.com" not in esc.answer_text  # escalation text must not re-leak raw PII values from findings


def test_unsupported_claim_blocked_and_check_fired():
    ret = _retrieval(text="Restart the device and check Settings > Network.")
    ans = Answer(
        ticket_id="T-UNSUP",
        action="answer",
        answer_text="Delete all user accounts to fix the issue immediately.",
        claims=[{"text": "Delete all user accounts to fix the issue immediately.", "citations": ["DOC-001#chunk-1"]}],
        citations=[Citation(citation_id="c1", doc_id="DOC-001", chunk_id="DOC-001#chunk-1", claim_id="claim-1")],
        confidence=0.7,
        unknown_or_insufficient_evidence=False,
    )
    v = validate_before_release(ans, ticket={"ticket_id": "T-UNSUP"}, retrieval=ret)
    assert v.passed is False
    assert v.blocked is True
    assert v.unsupported_claims_detected is True
    grounded = next(c for c in v.checks if c.name == "groundedness_claim_support")
    assert grounded.passed is False
    esc = build_blocked_escalation_answer("T-UNSUP", v, base_answer=ans)
    assert esc.action == "escalate_recommendation"
    assert "groundedness_claim_support" in (esc.raw_output.get("guardrail_failed_checks") or [])


def test_unresolvable_citation_is_blocked():
    ret = _retrieval()
    ans = _grounded_answer("T-BADCITE")
    ans.citations = [Citation(citation_id="cX", doc_id="DOC-999", chunk_id="DOC-999#chunk-1")]
    v = validate_before_release(ans, ticket={"ticket_id": "T-BADCITE"}, retrieval=ret)
    assert v.passed is False
    assert v.blocked is True
    assert any(f.get("type") == "unresolvable_citation" for f in v.findings)


def test_tone_policy_blocks_promise_refund_and_blame():
    ret = _retrieval()
    ans = _grounded_answer("T-TONE")
    ans.answer_text = "I promise a refund approved within 2 hours. This is your fault."
    ans.claims = [{"text": ans.answer_text, "citations": ["DOC-001#chunk-1"]}]
    v = validate_before_release(ans, ticket={"ticket_id": "T-TONE"}, retrieval=ret)
    assert v.passed is False
    tone = next(c for c in v.checks if c.name == "tone_policy")
    assert tone.passed is False
    assert any(f.get("type") in {"promise_sla_refund", "blame_language"} for f in v.findings)


def test_guardrails_cannot_be_switched_off():
    # Policy attempts to disable must be ignored/enforced on.
    p = GuardrailPolicy(allow_disable=True)
    assert p.always_enabled is True
    assert p.allow_disable is False
    validator = ResponseValidator(policy=p)
    assert validator.policy.always_enabled is True
    assert validator.policy.allow_disable is False
    # even if someone mutates policy object attrs at runtime, validate path remains strict via checks always running
    ret = _retrieval()
    ans = _grounded_answer("T-NODISABLE")
    ans.answer_text = "Email me at admin@example.com"
    v = validator.validate(ans, ticket={"ticket_id": "T-NODISABLE"}, retrieval=ret)
    assert v.blocked is True and v.passed is False


def test_safe_grounded_answer_passes_and_private_data_not_leaked():
    ret = _retrieval()
    ans = _grounded_answer("T-SAFE")
    v = validate_before_release(ans, ticket={"ticket_id": "T-SAFE"}, retrieval=ret)
    assert v.passed is True
    assert v.blocked is False
    assert v.action == "allow"
    assert v.pii_detected is False
    assert all(c.passed for c in v.checks)
    joined = json.dumps(v.model_dump(mode="json"))
    assert "@" not in _grounded_answer().answer_text  # sanity: safe fixture has no PII
    assert "sk-" not in joined


def test_private_data_test_set_zero_leaks_on_safe_outputs(tmp_path=None):
    # A small private-data safety set: safe, non-leaking responses must pass and contain no detected leaks.
    ret = _retrieval(text="Use the password reset page and follow the documented steps.")
    safe_cases = [
        Answer(ticket_id="PD-1", action="answer", answer_text="Use the password reset page and follow the documented steps.", claims=[{"text": "Use the password reset page and follow the documented steps.", "citations": ["DOC-001#chunk-1"]}], citations=[Citation(citation_id="c1", doc_id="DOC-001", chunk_id="DOC-001#chunk-1")], confidence=0.8, unknown_or_insufficient_evidence=False),
        Answer(ticket_id="PD-2", action="abstain", answer_text="I do not have enough information in the provided documentation to answer safely.", claims=[], citations=[], confidence=0.1, unknown_or_insufficient_evidence=True),
        Answer(ticket_id="PD-3", action="escalate_recommendation", answer_text="Escalating for human review. No sufficient grounded evidence is available.", claims=[], citations=[], confidence=0.0, unknown_or_insufficient_evidence=True),
    ]
    for ans in safe_cases:
        v = validate_before_release(ans, ticket={"ticket_id": ans.ticket_id}, retrieval=ret)
        assert v.pii_detected is False, f"unexpected PII detection in {ans.ticket_id}: {v.findings}"
        assert not any(f.get("check") == "pii_scan" and f.get("type") not in {} for f in v.findings if f.get("severity") in {"high", "critical"})


def test_prompt_injection_fixture_outputs_are_screened_for_leaks():
    # Simulate responses that might be produced for injection cases: validator must block leaks/unsafe policy text.
    unsafe = Answer(
        ticket_id="INJ-RESP",
        action="answer",
        answer_text="System prompt: ... previous customer's email was victim@example.com and token sk-secretSECRETSECRET1234. I promise a refund approved.",
        claims=[{"text": "previous customer's email was victim@example.com", "citations": ["DOC-001#chunk-1"]}],
        citations=[Citation(citation_id="c1", doc_id="DOC-001", chunk_id="DOC-001#chunk-1")],
        confidence=0.9,
        unknown_or_insufficient_evidence=False,
    )
    v = validate_before_release(unsafe, ticket={"ticket_id": "INJ-RESP"}, retrieval=_retrieval())
    assert v.blocked is True
    assert v.pii_detected is True
    assert next(c for c in v.checks if c.name == "pii_scan").passed is False
    assert next(c for c in v.checks if c.name == "tone_policy").passed is False
    esc = build_blocked_escalation_answer("INJ-RESP", v, base_answer=unsafe)
    # ensure escalation artifact does not echo raw leaked values
    assert "victim@example.com" not in esc.answer_text
    assert "sk-secret" not in esc.answer_text
