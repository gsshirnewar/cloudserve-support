import time
from concurrent.futures import ThreadPoolExecutor

from src.config import get_config
from src.pipeline.orchestrator import PipelineOrchestrator
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
