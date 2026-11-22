# ADR-006: Append-only decision logging for A8 auditability

- **Status:** Accepted (T10 draft)
- **Date:** 2026-11-22
- **Deciders:** Project delivery (design stage)
- **Related REQs:** REQ-X-LOG-001, REQ-X-MON-001, REQ-F-RTE-002, REQ-F-VAL-002, REQ-NF-EXPL-001
- **Evidence:** EV-05, EV-07, EV-15, EV-16, EV-21, EV-25, EV-31, EV-32

## Context
Compliance, trust, and debugging require explaining why the system answered, assisted, escalated, or blocked. A8 mandates logging inputs, predictions/confidence, sources, actions, and reasons; harness metrics must reconcile to recorded outcomes.

## Decision
Persist an **append-only decision record** per ticket/run containing normalized input refs/hash, classification (with alternatives/confidence), retrieval evidence/citations, routing rationale/thresholds, generation/validation outcomes, guardrail checks, errors/fallbacks, model/prompt versions, and latency/timing metadata (schema aligned to draft).

## Rationale
- Enables audit, governance reporting, and reproduction of decisions.
- Supports “show working” escalation packages and manager-readable explanations.
- Provides source-of-truth for metrics reconciliation (A9).

## Consequences
- **Positive:** Strong traceability and operational visibility.
- **Negative:** Storage/PII-minimization design care required.
- **Mitigations:** Store hashes/IDs and minimized necessary text, redact sensitive fields, index by run/ticket/outcome for queries.

## Alternatives considered
- **Unstructured logs only:** insufficient for reliable querying/reconciliation.
- **Mutable records:** rejected to preserve audit integrity.