from pathlib import Path

from src.config import get_config, reset_config_cache
from src.logging_config import configure_logging, get_logger
from src.schemas import Answer, Classification, DecisionRecord, NormalisedTicket, RetrievalResult, RouteDecision, Ticket, ValidationResult


def test_config_loads_defaults_and_paths():
    reset_config_cache()
    config = get_config()
    assert config.provider.llm_provider in {"openrouter", "groq"}
    assert isinstance(config.paths.project_root, Path)
    assert config.models.embedding_dimension == 384


def test_logging_configures_without_error():
    configure_logging(level="INFO", log_format="json")
    logger = get_logger("tests.skeleton")
    logger.info("skeleton logging smoke", extra={"component": "tests", "event": "smoke"})


def test_core_schemas_instantiate():
    ticket = Ticket(ticket_id="t1", channel="email", subject="hi", body="hello")
    norm = NormalisedTicket(ticket_id="t1", channel="email", raw_text="hello", original=ticket.model_dump())
    cls = Classification(
        ticket_id="t1",
        intent="billing_question",
        urgency="medium",
        intent_confidence=0.9,
        urgency_confidence=0.8,
        overall_confidence=0.85,
    )
    retrieval = RetrievalResult(ticket_id="t1", hits=[], sufficient_evidence=False)
    route = RouteDecision(ticket_id="t1", route="escalate", reason="insufficient evidence")
    answer = Answer(ticket_id="t1", action="abstain", answer_text="", confidence=0.0)
    validation = ValidationResult(ticket_id="t1", passed=True, blocked=False, action="allow")
    record = DecisionRecord(decision_id="d1", ticket_id="t1", final_outcome="escalated")
    assert norm.ticket_id == "t1"
    assert cls.intent == "billing_question"
    assert retrieval.sufficient_evidence is False
    assert route.route == "escalate"
    assert answer.unknown_or_insufficient_evidence is True
    assert validation.pii_detected is False
    assert record.ticket_id == "t1"
