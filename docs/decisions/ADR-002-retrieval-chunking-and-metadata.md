# ADR-002: Metadata-rich chunked retrieval over curated KB

- **Status:** Accepted (initial hypothesis, to validate)
- **Date:** 2026-11-22
- **Deciders:** Project delivery (design stage)
- **Related REQs:** REQ-F-RET-001/002, REQ-F-GEN-001/002, REQ-NF-MAINT-001
- **Evidence:** EV-19, EV-20, EV-21, EV-35, EV-36, EV-39

## Context
Corpus has 29 short, single-blob KB articles (~953–1470 chars) with metadata (`doc_id,title,category,applies_to,related_docs,last_reviewed_days_ago`). Retrieval must return ranked, resolvable passages and support citations and relevance thresholding.

## Decision
Index **small metadata-rich chunks** (~300–600 chars, ~75–150 tokens, 10–20% overlap) with chunk IDs and full doc metadata; include whole-doc fallback for very short articles. Filter by relevance threshold and return empty when insufficient.

## Rationale
- Improves citation granularity and boundary robustness vs whole-doc-only in some queries.
- Preserves traceability (doc/chunk IDs) and governance metadata for audit/freshness.
- Small corpus keeps index/simple chunking cost low.

## Consequences
- **Positive:** Verifiable citations, better control over irrelevant retrieval, extensible metadata filters.
- **Negative:** Chunking choices affect recall/precision and require tuning.
- **Mitigations:** Make chunk params configurable; evaluate chunk size/overlap/threshold on dev data (T11/T17+).

## Alternatives considered
- **Whole-document retrieval only:** simpler but weaker citation granularity and potential noise.
- **Large chunks/no overlap:** lower index size but higher boundary-loss risk.