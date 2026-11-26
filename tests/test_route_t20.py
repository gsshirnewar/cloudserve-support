from src.route.router import RoutingPolicy, route_ticket
from src.schemas import Classification, RetrievalResult, RetrievedChunk


def _cls(ticket_id="T-1", intent="billing_query", urgency="medium", conf=0.9, fallback=False):
    return Classification(
        ticket_id=ticket_id,
        intent=intent,
        urgency=urgency,
        intent_confidence=conf,
        urgency_confidence=conf,
        overall_confidence=conf,
        fallback_used=fallback,
        fallback_reason="fb" if fallback else None,
        uncertainty_flags=["classification_fallback"] if fallback else [],
        prompt_version="P-CLS-001@v1.0.0",
    )


def _ret(ticket_id="T-1", sufficient=True, n_hits=1, score=0.8):
    hits = [
        RetrievedChunk(doc_id="DOC-1", chunk_id="DOC-1#chunk_0", title="T", text="x", score=score)
        for _ in range(n_hits)
    ] if n_hits else []
    return RetrievalResult(
        ticket_id=ticket_id,
        query="q",
        hits=hits,
        top_score=score if n_hits else None,
        sufficient_evidence=sufficient and n_hits > 0,
        relevance_threshold=0.3,
    )


def test_route_identical_inputs_produce_identical_outputs():
    ticket = {"ticket_id": "T-100", "channel": "email"}
    cls = _cls(ticket_id="T-100", conf=0.92)
    ret = _ret(ticket_id="T-100", sufficient=True, n_hits=2)
    policy = RoutingPolicy(route_auto_min_confidence=0.85, route_assist_min_confidence=0.6)
    d1 = route_ticket(ticket, cls, ret, policy=policy)
    d2 = route_ticket(ticket, cls, ret, policy=policy)
    assert d1.model_dump() == d2.model_dump()
    assert d1.route == "auto_answer"
    assert d1.deterministic_inputs["action"] == d1.route
    assert d1.deterministic_inputs["target"]
    assert d1.thresholds_applied["route_auto_min_confidence"] == 0.85
    assert d1.reason


def test_no_doc_and_must_not_auto_cases_blocked():
    policy = RoutingPolicy()

    # must-not-auto blocked
    ticket_mna = {"ticket_id": "T-200", "must_not_auto_respond": True}
    d_mna = route_ticket(ticket_mna, _cls("T-200", conf=0.99), _ret("T-200"), policy=policy)
    assert d_mna.route == "block"
    assert "must_not_auto" in " ".join(d_mna.policy_flags) or d_mna.deterministic_inputs["must_not_auto"] is True

    # prohibited intent blocked
    d_sec = route_ticket({"ticket_id": "T-201"}, _cls("T-201", intent="security_incident", conf=0.99), _ret("T-201"), policy=policy)
    assert d_sec.route == "block"

    # no sufficient evidence/no-doc blocked
    d_nodoc = route_ticket({"ticket_id": "T-202"}, _cls("T-202", conf=0.95), _ret("T-202", sufficient=False, n_hits=0, score=None), policy=policy)
    assert d_nodoc.route == "block"

    d_not_answerable = route_ticket({"ticket_id": "T-203", "answerable_from_docs": False}, _cls("T-203", conf=0.95), _ret("T-203"), policy=policy)
    assert d_not_answerable.route == "block"


def test_ground_truth_labels_do_not_control_routing():
    cls = _cls("T-204", conf=0.95)
    ret = _ret("T-204")

    labelled_answerable = route_ticket(
        {"ticket_id": "T-204", "labels": {"answerable_from_docs": False}},
        cls,
        ret,
    )
    labelled_restricted = route_ticket(
        {"ticket_id": "T-204", "labels": {"must_not_auto_respond": True}},
        cls,
        ret,
    )

    assert labelled_answerable.route == "auto_answer"
    assert labelled_restricted.route == "auto_answer"


def test_confidence_bands_and_fallback_routing():
    policy = RoutingPolicy(route_auto_min_confidence=0.85, route_assist_min_confidence=0.6)
    ret = _ret("T-300")
    assert route_ticket({"ticket_id": "T-300"}, _cls("T-300", conf=0.9), ret, policy=policy).route == "auto_answer"
    assert route_ticket({"ticket_id": "T-301"}, _cls("T-301", conf=0.7), ret, policy=policy).route == "assist_draft"
    assert route_ticket({"ticket_id": "T-302"}, _cls("T-302", conf=0.4), ret, policy=policy).route == "escalate"
    # fallback/unknown classification escalated (not auto)
    fb = route_ticket({"ticket_id": "T-303"}, _cls("T-303", intent="unknown_intent", conf=0.0, fallback=True), ret, policy=policy)
    assert fb.route == "escalate"
