"""Retrieval package (chunking, embedding/indexing, search)."""

from .chunking import DocChunk, chunk_document, chunk_documents, load_documentation_corpus
from .retriever import RetrievalIndex, RetrievedChunk, build_or_load_index

__all__ = [
    "DocChunk",
    "chunk_document",
    "chunk_documents",
    "load_documentation_corpus",
    "RetrievalIndex",
    "RetrievedChunk",
    "build_or_load_index",
]
