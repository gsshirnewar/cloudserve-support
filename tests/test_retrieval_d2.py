import json
from pathlib import Path

from src.retrieve.chunking import chunk_documents, load_documentation_corpus
from src.retrieve.retriever import RetrievalIndex


def test_chunks_cover_all_29_docs_with_stable_ids():
    docs = load_documentation_corpus(Path(__file__).resolve().parents[1] / "data" / "documentation.json")
    chunks = chunk_documents(docs)
    assert len(docs) == 29
    doc_ids = {d["doc_id"] for d in docs}
    chunk_doc_ids = {c.doc_id for c in chunks}
    assert chunk_doc_ids == doc_ids
    assert len({c.chunk_id for c in chunks}) == len(chunks)
    assert all("#chunk_" in c.chunk_id for c in chunks)


def test_index_build_reopen_search_and_offtopic_threshold(tmp_path):
    corpus = Path(__file__).resolve().parents[1] / "data" / "documentation.json"
    idx = RetrievalIndex(persist_dir=tmp_path / "index", corpus_path=corpus, relevance_threshold=0.2)
    meta = idx.build(force_rebuild=True)
    assert meta["doc_count"] == 29
    assert meta["chunk_count"] > 0

    # reopen/idempotent load
    idx2 = RetrievalIndex(persist_dir=tmp_path / "index", corpus_path=corpus, relevance_threshold=0.2)
    assert idx2.load() is True
    assert len(idx2._chunks_by_id) == meta["chunk_count"]  # internal but stable for this test

    hits = idx2.search("How do I rotate API keys?", top_k=3)
    assert len(hits) >= 1
    assert hits[0].chunk_id
    resolved = idx2.resolve_chunk(hits[0].chunk_id)
    assert resolved is not None
    assert str(resolved.get("text") or "")

    off_topic = idx2.search("best pizza recipe for weekend party", top_k=3, relevance_threshold=0.95)
    assert off_topic == []
