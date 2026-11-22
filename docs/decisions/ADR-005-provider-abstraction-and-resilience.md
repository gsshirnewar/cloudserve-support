# ADR-005: OpenRouter-first provider abstraction with cache, backoff, and degraded mode

- **Status:** Accepted (T10 draft)
- **Date:** 2026-11-22
- **Deciders:** Project delivery (design stage)
- **Related REQs:** REQ-F-OPS-001, REQ-NF-REL-001, REQ-NF-PERF-001, REQ-NF-MAINT-001
- **Evidence:** EV-01, EV-23, EV-29; Brief/Spec free-tier and A11 constraints

## Context
System depends on external LLM/embedding providers subject to rate limits, timeouts, and outages. Project must run on free-tier/open-source constraints and handle failures gracefully without crashing unattended runs.

## Decision
Use a **provider abstraction layer** with OpenRouter default (Groq/alternatives configurable), disk response cache, bounded retries with exponential backoff+jitter, rate/concurrency limiting, per-call timeouts, and **typed degraded/offline results** (including provider-down simulation for tests).

## Rationale
- Isolates vendor differences and supports swap without pipeline rewrite.
- Caching reduces cost/rate pressure and improves reproducibility.
- Degraded mode ensures A11-compliant continuation and testability.

## Consequences
- **Positive:** Resilience, controllable spend/rate usage, reproducible development runs.
- **Negative:** Cache invalidation/versioning complexity; degraded responses may reduce automation coverage.
- **Mitigations:** Cache keys include model/prompt/version/params/input hash; log all fallback/degraded events; expose simulation switches in tests.

## Alternatives considered
- **Direct provider calls in components:** simpler initially but brittle and non-compliant with resilience/swap goals.
- **Paid-capacity dependence:** out of scope and unnecessary per constraints.