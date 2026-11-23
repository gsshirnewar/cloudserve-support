"""Documentation chunking utilities for retrieval (T18)."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


@dataclass
class DocChunk:
    chunk_id: str
    doc_id: str
    chunk_index: int
    title: str
    category: str
    applies_to: List[str]
    related_docs: List[str]
    last_reviewed_days_ago: Any
    text: str
    char_start: int
    char_end: int

    def to_metadata(self) -> Dict[str, Any]:
        data = asdict(self)
        # keep searchable text separate for stores that distinguish documents/metadata
        text = data.pop("text")
        data["text"] = text
        return data


def load_documentation_corpus(path: Path | str) -> List[Dict[str, Any]]:
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # preserve paragraph breaks but normalize spaces/tabs
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_units(text: str) -> List[str]:
    """Split into paragraph/sentence-like units while keeping content order."""
    if not text:
        return [""]
    # Prefer paragraph boundaries, then sentence-ish boundaries.
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paras:
        paras = [text.strip()]
    units: List[str] = []
    for para in paras:
        # sentence split heuristic
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\(\[])", para)
        parts = [p.strip() for p in parts if p.strip()]
        if parts:
            units.extend(parts)
        else:
            units.append(para.strip())
    return units or [text]


def chunk_text(
    text: str,
    *,
    chunk_size: int = 500,
    overlap: int = 80,
    min_chunk_size: int = 120,
) -> List[tuple[int, int, str]]:
    """Return list of (char_start, char_end, chunk_text) with overlap.

    Character spans are approximate relative to normalized text; chunk_id is the stable key.
    """
    normalized = _normalize_whitespace(text)
    if not normalized:
        return [(0, 0, "")]
    if len(normalized) <= chunk_size:
        return [(0, len(normalized), normalized)]

    units = _split_units(normalized)
    chunks: List[str] = []
    current = ""
    for unit in units:
        if not current:
            candidate = unit
        else:
            candidate = current + "\n" + unit
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        # flush current
        if current:
            chunks.append(current.strip())
            # seed next with overlap tail + current unit
            tail = current[-overlap:] if overlap > 0 else ""
            current = (tail + "\n" + unit).strip() if tail else unit
            # if a single unit is too large, hard-wrap it
            while len(current) > chunk_size:
                chunks.append(current[:chunk_size].strip())
                current = current[chunk_size - overlap :].strip() if overlap < chunk_size else current[chunk_size:].strip()
        else:
            # unit itself too large
            tmp = unit
            while len(tmp) > chunk_size:
                chunks.append(tmp[:chunk_size].strip())
                tmp = tmp[chunk_size - overlap :].strip() if overlap < chunk_size else tmp[chunk_size:].strip()
            current = tmp
    if current:
        chunks.append(current.strip())

    # Merge tiny trailing chunks into previous chunk when possible
    merged: List[str] = []
    for ch in chunks:
        if not ch:
            continue
        if merged and len(ch) < min_chunk_size and len(merged[-1]) + 1 + len(ch) <= chunk_size + overlap:
            merged[-1] = (merged[-1] + "\n" + ch).strip()
        else:
            merged.append(ch)
    if not merged:
        merged = [normalized]

    # Compute approximate spans by searching forward in normalized text
    result: List[tuple[int, int, str]] = []
    cursor = 0
    for ch in merged:
        probe = ch[: min(40, len(ch))]
        idx = normalized.find(probe, cursor)
        if idx == -1:
            idx = cursor
        start = idx
        end = min(len(normalized), start + len(ch))
        result.append((start, end, ch))
        cursor = max(cursor, start + max(1, len(ch) - overlap))
    return result


def chunk_document(
    doc: Dict[str, Any], *, chunk_size: int = 500, overlap: int = 80
) -> List[DocChunk]:
    doc_id = str(doc.get("doc_id") or doc.get("article_id") or "UNKNOWN_DOC")
    title = str(doc.get("title") or "")
    category = str(doc.get("category") or "")
    applies_to = list(doc.get("applies_to") or [])
    related_docs = list(doc.get("related_docs") or [])
    last_reviewed = doc.get("last_reviewed_days_ago")
    content = str(doc.get("content") or "")

    spans = chunk_text(content, chunk_size=chunk_size, overlap=overlap)
    chunks: List[DocChunk] = []
    for i, (start, end, text) in enumerate(spans):
        chunk_id = f"{doc_id}#chunk_{i}"
        chunks.append(
            DocChunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                chunk_index=i,
                title=title,
                category=category,
                applies_to=[str(x) for x in applies_to],
                related_docs=[str(x) for x in related_docs],
                last_reviewed_days_ago=last_reviewed,
                text=text,
                char_start=start,
                char_end=end,
            )
        )
    return chunks


def chunk_documents(
    docs: Sequence[Dict[str, Any]], *, chunk_size: int = 500, overlap: int = 80
) -> List[DocChunk]:
    all_chunks: List[DocChunk] = []
    for doc in docs:
        all_chunks.extend(chunk_document(doc, chunk_size=chunk_size, overlap=overlap))
    return all_chunks
