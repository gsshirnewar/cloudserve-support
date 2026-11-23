import json

from src.classify.calibration import expected_calibration_error, fit_temperature, reliability_curve
from src.classify.classifier import TicketClassifier, _fallback_classification
from src.llm.provider import LLMProvider, SimulationBackend


def test_classifier_structured_output_parses_and_validates():
    payload = {
        "prompt_id": "P-CLS-001",
        "prompt_version": "v1.0.0",
        "ticket_id": "T-1",
        "intent": "billing_query",
        "intent_confidence": 0.91,
        "urgency": "medium",
        "urgency_confidence": 0.88,
        "overall_confidence": 0.9,
        "alternatives": [
            {"intent": "billing_query", "urgency": "medium", "score": 0.9, "reason": "primary"},
            {"intent": "quota_or_overage", "urgency": "medium", "score": 0.2, "reason": "secondary"},
        ],
        "uncertainty_flags": [],
        "fallback_used": False,
        "fallback_reason": None,
        "notes_for_routing": "clear billing question",
    }
    provider = LLMProvider(
        backend=SimulationBackend(mode="off", success_text=json.dumps(payload)),
    )
    clf = TicketClassifier(provider=provider)
    out = clf.classify_ticket({"ticket_id": "T-1", "channel": "email", "subject": "Invoice", "body": "Need invoice"})
    assert out.ticket_id == "T-1"
    assert out.intent == "billing_query"
    assert out.urgency == "medium"
    assert 0.0 <= out.overall_confidence <= 1.0
    assert 0.0 <= out.intent_confidence <= 1.0
    assert 0.0 <= out.urgency_confidence <= 1.0
    assert len(out.intent_alternatives) >= 1
    assert len(out.urgency_alternatives) >= 1
    assert out.fallback_used is False
    assert out.prompt_version is not None


def test_classifier_returns_safe_fallback_on_malformed_or_failure():
    # malformed JSON / parse failure -> fallback
    provider = LLMProvider(
        backend=SimulationBackend(mode="off", success_text="not json !!!"),
    )
    clf = TicketClassifier(provider=provider)
    out = clf.classify_ticket({"ticket_id": "T-2", "channel": "chat", "body": ""})
    assert out.intent == "unknown_intent"
    assert out.urgency == "unknown_urgency"
    assert out.fallback_used is True
    assert out.overall_confidence == 0.0
    assert out.fallback_reason
    assert len(out.intent_alternatives) >= 1

    # provider failure simulation -> fallback
    provider2 = LLMProvider(backend=SimulationBackend(mode="timeout"))
    clf2 = TicketClassifier(provider=provider2)
    out2 = clf2.classify_ticket(
        {"ticket_id": "T-3", "channel": "email", "body": "help"},
        simulation_mode="timeout",
    )
    assert out2.fallback_used is True
    assert out2.intent == "unknown_intent"
    assert out2.urgency == "unknown_urgency"


def test_calibration_metrics_and_temperature_fit():
    conf = [0.9, 0.8, 0.7, 0.6, 0.4, 0.3]
    correct = [1, 1, 1, 0, 0, 0]
    ece = expected_calibration_error(conf, correct, n_bins=3)
    assert ece >= 0.0
    t = fit_temperature(conf, correct)
    assert t > 0
    bins = reliability_curve(conf, correct, n_bins=3)
    assert len(bins) == 3
    assert sum(b.count for b in bins) == len(conf)
