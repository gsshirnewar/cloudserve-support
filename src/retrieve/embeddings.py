"""Embedding providers for retrieval indexing/search."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Iterable, List, Sequence

import numpy as np

from src.config import get_config


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9_]+", (text or "").lower())


class BaseEmbedder:
    model_name: str
    dimension: int

    def embed_texts(self, texts: Sequence[str]) -> np.ndarray:
        raise NotImplementedError

    def embed_query(self, text: str) -> np.ndarray:
        vec = self.embed_texts([text])[0]
        return vec


class HashingEmbedder(BaseEmbedder):
    """Deterministic local fallback embedder (no external model dependencies)."""

    def __init__(self, dimension: int = 384, model_name: str = "local-hash-fallback"):
        self.dimension = int(dimension)
        self.model_name = model_name

    def _embed_one(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dimension, dtype=np.float32)
        tokens = _tokenize(text)
        if not tokens:
            return vec
        for tok in tokens:
            h = hashlib.sha256(tok.encode("utf-8")).digest()
            idx = int.from_bytes(h[:4], "little") % self.dimension
            sign = 1.0 if (h[4] % 2 == 0) else -1.0
            vec[idx] += sign
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        return vec

    def embed_texts(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)
        arr = np.vstack([self._embed_one(t) for t in texts]).astype(np.float32)
        return arr


class SentenceTransformerEmbedder(BaseEmbedder):
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer  # type: ignore

        self.model_name = model_name
        self._model = SentenceTransformer(model_name)
        # probe dimension
        dim = getattr(self._model, "get_sentence_embedding_dimension", lambda: None)()
        if dim is None:
            sample = self._model.encode(["probe"], normalize_embeddings=True)
            dim = int(np.asarray(sample).shape[1])
        self.dimension = int(dim)

    def embed_texts(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)
        vectors = self._model.encode(
            list(texts),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)


@dataclass
class EmbedderInfo:
    model_name: str
    dimension: int
    backend: str  # sentence_transformers|hash_fallback


def create_embedder(prefer_sentence_transformers: bool = True) -> tuple[BaseEmbedder, EmbedderInfo]:
    config = get_config()
    configured_name = config.models.embedding_model_name
    configured_dim = config.models.embedding_dimension
    if prefer_sentence_transformers:
        try:
            embedder = SentenceTransformerEmbedder(configured_name)
            return embedder, EmbedderInfo(embedder.model_name, embedder.dimension, "sentence_transformers")
        except Exception:
            pass
    fallback = HashingEmbedder(dimension=configured_dim, model_name=f"{configured_name} (hash-fallback)")
    return fallback, EmbedderInfo(fallback.model_name, fallback.dimension, "hash_fallback")
