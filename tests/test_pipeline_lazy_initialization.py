import time
from concurrent.futures import ThreadPoolExecutor

from src.config import get_config
from src.pipeline.orchestrator import PipelineOrchestrator
from src.schemas import Classification
from src.store.decision_log import DecisionLogStore


def test_retriever_is_initialized_once_under_concurrent_requests(tmp_path, monkeypatch):
    import src.retrieve

    instances = []

    class FakeRetriever:
        def __init__(self):
            instances.append(self)

        def open(self):
            time.sleep(0.02)

    monkeypatch.setattr(src.retrieve, "RetrievalIndex", FakeRetriever)
    orchestrator = PipelineOrchestrator(
        config=get_config(),
        store=DecisionLogStore(db_path=tmp_path / "decisions.db"),
    )

    with ThreadPoolExecutor(max_workers=8) as executor:
        retrievers = list(executor.map(lambda _: orchestrator._get_retriever(), range(16)))

    assert len(instances) == 1
    assert all(retriever is instances[0] for retriever in retrievers)


def test_classifier_fallback_marks_ticket_degraded(tmp_path):
    class FallbackClassifier:
        def classify_ticket(self, ticket):
            return Classification(
                ticket_id=ticket["ticket_id"],
                intent="unknown_intent",
                urgency="unknown_urgency",
                intent_confidence=0.0,
                urgency_confidence=0.0,
                overall_confidence=0.0,
                fallback_used=True,
                fallback_reason="provider unavailable",
            )

    orchestrator = PipelineOrchestrator(
        config=get_config(),
        classifier=FallbackClassifier(),
        store=DecisionLogStore(db_path=tmp_path / "decisions.db"),
    )
    state = {
        "ticket": {"ticket_id": "OFFLINE-1"},
        "ticket_id": "OFFLINE-1",
        "node_outcomes": {},
        "degraded": False,
    }

    orchestrator._node_classify(state)

    assert state["degraded"] is True
    assert state["node_outcomes"]["classify"]["fallback_used"] is True
    assert state["node_outcomes"]["classify"]["ok"] is False
