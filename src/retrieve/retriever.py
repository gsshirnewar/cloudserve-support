"""Retrieval index and search (T18 / D2).

Prefers Chroma + sentence-transformers/MiniLM when available, with a local
persistent numpy/JSON fallback so indexing/search remains runnable in constrained
environments. Chunk IDs are stable (`{doc_id}#chunk_{n}`) and resolvable.
"""

from __future__ import annotations

import json
import math
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from src.config import get_config
from src.logging_config import get_logger

from .chunking import DocChunk, chunk_documents, load_documentation_corpus
from .embeddings import BaseEmbedder, EmbedderInfo, create_embedder

logger = get_logger(__name__)


@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_id: str
    title: str
    category: str
    text: str
    score: float
    rank: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class _LocalPersistentIndex:
    """Simple persisted local vector index (idempotent deterministic rebuild)."""

    def __init__(self, persist_dir: Path):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.chunks_path = self.persist_dir / "chunks.json"
        self.embeddings_path = self.persist_dir / "embeddings.npy"
        self.meta_path = self.persist_dir / "index_meta.json"

    @property
    def exists(self) -> bool:
        return self.chunks_path.exists() and self.embeddings_path.exists() and self.meta_path.exists()

    def save(self, chunks: Sequence[DocChunk], embeddings: np.ndarray, meta: Dict[str, Any]) -> None:
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        payload = [asdict(c) for c in chunks]
        self.chunks_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        np.save(self.embeddings_path, embeddings.astype(np.float32))
        self.meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self) -> tuple[List[Dict[str, Any]], np.ndarray, Dict[str, Any]]:
        chunks = json.loads(self.chunks_path.read_text(encoding="utf-8"))
        embeddings = np.load(self.embeddings_path)
        meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
        return chunks, embeddings.astype(np.float32), meta

    def clear(self) -> None:
        if self.persist_dir.exists():
            shutil.rmtree(self.persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)


class _ChromaIndex:
    def __init__(self, persist_dir: Path, collection_name: str = "cloudserve_docs"):
        import chromadb  # type: ignore

        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        try:
            return int(self.collection.count())
        except Exception:
            return 0

    def rebuild(self, chunks: Sequence[DocChunk], embeddings: np.ndarray, meta: Dict[str, Any]) -> None:
        # idempotent deterministic rebuild: clear collection contents then add all chunks once
        try:
            existing = self.collection.get(include=[])
            ids = existing.get("ids") or []
            if ids:
                self.collection.delete(ids=ids)
        except Exception:
            # fallback: recreate collection
            try:
                name = self.collection.name
                self.client.delete_collection(name)
                self.collection = self.client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})
            except Exception:
                pass

        ids = [c.chunk_id for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = []
        for c in chunks:
            m = asdict(c)
            # chroma metadata values must be scalar/simple types
            m["applies_to"] = json.dumps(c.applies_to, ensure_ascii=False)
            m["related_docs"] = json.dumps(c.related_docs, ensure_ascii=False)
            m["last_reviewed_days_ago"] = "" if c.last_reviewed_days_ago is None else str(c.last_reviewed_days_ago)
            metadatas.append(m)
        # upsert preferred if available, else add after clear
        try:
            self.collection.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings.tolist())
        except Exception:
            self.collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings.tolist())
        # store sidecar meta for reopen/info
        meta_path = self.persist_dir / "index_meta.json"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def query(self, query_embedding: np.ndarray, top_k: int) -> List[Tuple[str, float, Dict[str, Any], str]]:
        res = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        ids = (res.get("ids") or [[]])[0]
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        out = []
        for cid, dist, md, doc in zip(ids, dists, metas, docs):
            # cosine distance -> similarity (for hnsw:space=cosine, distance ~ 1-cos_sim)
            try:
                score = 1.0 - float(dist)
            except Exception:
                score = 0.0
            # normalize metadata fields we serialized
            if isinstance(md, dict):
                for k in ("applies_to", "related_docs"):
                    v = md.get(k)
                    if isinstance(v, str):
                        try:
                            md[k] = json.loads(v)
                        except Exception:
                            pass
            out.append((str(cid), float(score), md or {}, doc or ""))
        return out

    def get(self, chunk_id: str) -> Optional[Tuple[Dict[str, Any], str]]:
        res = self.collection.get(ids=[chunk_id], include=["documents", "metadatas"])
        ids = res.get("ids") or []
        if not ids:
            return None
        md = (res.get("metadatas") or [{}])[0] or {}
        doc = (res.get("documents") or [""])[0] or ""
        for k in ("applies_to", "related_docs"):
            v = md.get(k)
            if isinstance(v, str):
                try:
                    md[k] = json.loads(v)
                except Exception:
                    pass
        return md, doc


class RetrievalIndex:
    def __init__(
        self,
        *,
        persist_dir: Optional[Path] = None,
        corpus_path: Optional[Path] = None,
        chunk_size: int = 500,
        chunk_overlap: int = 80,
        relevance_threshold: Optional[float] = None,
        prefer_chroma: bool = True,
    ):
        config = get_config()
        self.persist_dir = Path(persist_dir or config.paths.chroma_persist_dir)
        self.corpus_path = Path(corpus_path or (config.paths.data_dir / "documentation.json"))
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.relevance_threshold = (
            float(config.thresholds.retrieval_relevance_threshold)
            if relevance_threshold is None
            else float(relevance_threshold)
        )
        self.prefer_chroma = prefer_chroma

        self.embedder: Optional[BaseEmbedder] = None
        self.embedder_info: Optional[EmbedderInfo] = None
        self.backend: str = "local"
        self._local: Optional[_LocalPersistentIndex] = None
        self._chroma: Optional[_ChromaIndex] = None
        self._chunks_by_id: Dict[str, Dict[str, Any]] = {}
        self._embeddings: Optional[np.ndarray] = None
        self._meta: Dict[str, Any] = {}

    def _ensure_embedder(self) -> None:
        if self.embedder is None:
            self.embedder, self.embedder_info = create_embedder(prefer_sentence_transformers=True)

    def _try_open_chroma(self) -> bool:
        if not self.prefer_chroma:
            return False
        try:
            self._chroma = _ChromaIndex(self.persist_dir)
            self.backend = "chroma"
            return True
        except Exception:
            self._chroma = None
            return False

    def _open_local(self) -> None:
        self._local = _LocalPersistentIndex(self.persist_dir)
        self.backend = "local"

    @property
    def is_ready(self) -> bool:
        if self.backend == "chroma" and self._chroma is not None:
            return self._chroma.count() > 0
        return bool(self._chunks_by_id) and self._embeddings is not None

    def build(self, force_rebuild: bool = True) -> Dict[str, Any]:
        """Build/rebuild index from corpus (idempotent deterministic rebuild)."""
        self._ensure_embedder()
        docs = load_documentation_corpus(self.corpus_path)
        chunks = chunk_documents(docs, chunk_size=self.chunk_size, overlap=self.chunk_overlap)
        texts = [c.text for c in chunks]
        embeddings = self.embedder.embed_texts(texts) if texts else np.zeros((0, self.embedder_info.dimension), dtype=np.float32)  # type: ignore[union-attr]

        meta = {
            "backend": None,
            "corpus_path": str(self.corpus_path),
            "doc_count": len(docs),
            "chunk_count": len(chunks),
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "embedding_model": self.embedder_info.model_name if self.embedder_info else "unknown",
            "embedding_dimension": int(embeddings.shape[1]) if embeddings.ndim == 2 and embeddings.size else 0,
            "embedding_backend": self.embedder_info.backend if self.embedder_info else "unknown",
        }

        if self._try_open_chroma():
            self._chroma.rebuild(chunks, embeddings, meta={**meta, "backend": "chroma"})  # type: ignore[union-attr]
            meta["backend"] = "chroma"
        else:
            self._open_local()
            # clear+save for deterministic rebuild without duplicates
            self._local.clear()  # type: ignore[union-attr]
            self._local.save(chunks, embeddings, meta={**meta, "backend": "local"})  # type: ignore[union-attr]
            meta["backend"] = "local"

        self._meta = meta
        self._chunks_by_id = {c.chunk_id: asdict(c) for c in chunks}
        self._embeddings = embeddings
        self._save_chunk_map(chunks)
        logger.info("Retrieval index built", extra={"component": "retrieve", "event": "index_built", **meta})
        return meta

    def _save_chunk_map(self, chunks: Sequence[DocChunk]) -> None:
        # Always persist a resolvable chunk map alongside backend storage
        sidecar = self.persist_dir / "chunk_map.json"
        sidecar.write_text(json.dumps([asdict(c) for c in chunks], ensure_ascii=False), encoding="utf-8")

    def load(self) -> bool:
        """Load existing persisted index; returns True if loaded."""
        self._ensure_embedder()
        sidecar = self.persist_dir / "chunk_map.json"
        meta_path = self.persist_dir / "index_meta.json"
        if sidecar.exists():
            try:
                items = json.loads(sidecar.read_text(encoding="utf-8"))
                self._chunks_by_id = {str(x["chunk_id"]): x for x in items}
            except Exception:
                self._chunks_by_id = {}

        if meta_path.exists():
            try:
                self._meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                self._meta = {}

        # Try chroma first if available
        if self._try_open_chroma() and self._chroma is not None and self._chroma.count() > 0:
            self.backend = "chroma"
            return True

        self._open_local()
        if self._local and self._local.exists:  # type: ignore[truthy-bool]
            try:
                chunks, embeddings, meta = self._local.load()  # type: ignore[union-attr]
                self._chunks_by_id = {str(x["chunk_id"]): x for x in chunks} or self._chunks_by_id
                self._embeddings = embeddings
                self._meta = meta or self._meta
                self.backend = "local"
                return len(self._chunks_by_id) > 0
            except Exception:
                return False
        return False

    def ensure_ready(self, rebuild_if_missing: bool = True) -> Dict[str, Any]:
        if self.load():
            return {**self._meta, "loaded": True, "backend": self.backend}
        if rebuild_if_missing:
            meta = self.build(force_rebuild=True)
            meta["loaded"] = False
            return meta
        raise RuntimeError("Retrieval index not found and rebuild_if_missing=False")

    def _cosine_search_local(self, query_vec: np.ndarray, top_k: int) -> List[Tuple[str, float]]:
        if self._embeddings is None or len(self._chunks_by_id) == 0:
            return []
        # embeddings assumed normalized (sentence-transformers) or near-normalized; normalize defensively
        mat = self._embeddings
        q = query_vec.astype(np.float32)
        qn = np.linalg.norm(q) or 1.0
        q = q / qn
        denom = np.linalg.norm(mat, axis=1, keepdims=False)
        denom[denom == 0] = 1.0
        matn = mat / denom[:, None]
        scores = matn @ q
        idxs = np.argsort(-scores)[:top_k]
        ids = list(self._chunks_by_id.keys())
        # _chunks_by_id insertion order preserved (Python 3.7+); must align with embeddings/chunks save order
        results: List[Tuple[str, float]] = []
        for i in idxs:
            if i < 0 or i >= len(ids):
                continue
            results.append((ids[int(i)], float(scores[int(i)])))
        return results

    def resolve_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        if chunk_id in self._chunks_by_id:
            return self._chunks_by_id[chunk_id]
        if self.backend == "chroma" and self._chroma is not None:
            got = self._chroma.get(chunk_id)
            if got:
                md, text = got
                md = dict(md)
                md.setdefault("chunk_id", chunk_id)
                md.setdefault("text", text)
                return md
        return None

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        relevance_threshold: Optional[float] = None,
    ) -> List[RetrievedChunk]:
        if not query or not str(query).strip():
            return []
        self.ensure_ready(rebuild_if_missing=True)
        self._ensure_embedder()
        threshold = self.relevance_threshold if relevance_threshold is None else float(relevance_threshold)
        q_vec = self.embedder.embed_query(str(query))  # type: ignore[union-attr]

        raw: List[Tuple[str, float, Dict[str, Any], str]] = []
        if self.backend == "chroma" and self._chroma is not None:
            raw = self._chroma.query(q_vec, top_k=top_k)
        else:
            local_hits = self._cosine_search_local(q_vec, top_k=top_k)
            for cid, score in local_hits:
                resolved = self.resolve_chunk(cid) or {}
                raw.append((cid, score, resolved, str(resolved.get("text") or "")))

        results: List[RetrievedChunk] = []
        rank = 1
        for cid, score, md, text in raw:
            if score < threshold:
                continue
            resolved = self.resolve_chunk(cid) or md or {}
            doc_text = text or str(resolved.get("text") or md.get("text") or "")
            if not doc_text and cid in self._chunks_by_id:
                doc_text = str(self._chunks_by_id[cid].get("text") or "")
            results.append(
                RetrievedChunk(
                    chunk_id=str(cid),
                    doc_id=str(resolved.get("doc_id") or md.get("doc_id") or cid.split("#", 1)[0]),
                    title=str(resolved.get("title") or md.get("title") or ""),
                    category=str(resolved.get("category") or md.get("category") or ""),
                    text=doc_text,
                    score=float(score),
                    rank=rank,
                    metadata={
                        k: resolved.get(k, md.get(k))
                        for k in [
                            "chunk_index",
                            "applies_to",
                            "related_docs",
                            "last_reviewed_days_ago",
                            "char_start",
                            "char_end",
                        ]
                        if k in resolved or k in md
                    },
                )
            )
            rank += 1
        # ensure empty on no-hit/off-topic
        return results

    def info(self) -> Dict[str, Any]:
        return {
            **self._meta,
            "backend": self.backend,
            "persist_dir": str(self.persist_dir),
            "relevance_threshold": self.relevance_threshold,
            "ready": self.is_ready,
            "chunk_ids": len(self._chunks_by_id),
        }


def build_or_load_index(
    *,
    force_rebuild: bool = False,
    relevance_threshold: Optional[float] = None,
) -> RetrievalIndex:
    idx = RetrievalIndex(relevance_threshold=relevance_threshold)
    if force_rebuild:
        idx.build(force_rebuild=True)
    else:
        idx.ensure_ready(rebuild_if_missing=True)
    return idx
