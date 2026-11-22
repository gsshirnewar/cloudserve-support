# Component-to-Requirement Map (T10)

**Source PRD:** [../prd/PRD_v1.md](../prd/PRD_v1.md)  
**Traceability seed:** [../prd/traceability.csv](../prd/traceability.csv)

## 1. Pipeline components (6)

| Component | Responsibilities (design) | Input schema (LLD) | Output schema (LLD) | Failure behavior | REQ refs | A-criteria |
|---|---|---|---|---|---|---|
| Ingest | Accept 4 channels, normalize to one model, preserve raw text/channel, handle missing/unusual/empty inputs | `RawTicket` | `NormalizedTicket` | Fail-soft normalization with warnings; no crash | REQ-F-ING-001, REQ-F-ING-002 | A1, A11 |
| Classify | Intent + urgency + numeric confidence; fallback on failure; return alternatives considered | `NormalizedTicket` | `ClassificationResult` | Bounded retry/fallback (`unknown`, low confidence), records alternatives/errors | REQ-F-CLS-001, REQ-F-CLS-002 | A2, A11 |
| Retrieve | Ranked KB passages with scores and resolvable IDs; relevance threshold; return nothing when insufficient | `NormalizedTicket`, `ClassificationResult` | `RetrievalResult` (`RetrievalHit[]`) | No-hit/empty on low relevance; index/provider errors -> safe fallback | REQ-F-RET-001, REQ-F-RET-002 | A3, A4, A11 |
| Route | Deterministic auto-answer/assist/escalate/block decision from classification/retrieval/thresholds/policy; manager-readable reason; escalation package | `ClassificationResult`, `RetrievalResult`, policy config | `RouteDecision` (+ escalation context) | Pure deterministic function; safe default escalate on invalid state | REQ-F-RTE-001, REQ-F-RTE-002 | A3, A6, A8 |
| Generate | Grounded, cited, structured answer/draft/summary; state unknown when insufficient; isolate instructions from ticket text | Context + `RouteDecision` | `GenerationResult` | Abstain/fallback on provider/parse failure; no fabricated citations | REQ-F-GEN-001, REQ-F-GEN-002 | A4, A11 |
| Validate | Pre-release checks for PII/private data and unsupported claims; can block; records checks/findings/actions | `GenerationResult`, context | `ValidationResult` | Always-run; fail-safe block/escalate on validator errors | REQ-F-VAL-001, REQ-F-VAL-002 | A5, A7, A11 |

## 2. Cross-cutting concerns (3)

| Concern | Responsibilities (design) | Key artifacts/interfaces | Failure behavior | REQ refs | A-criteria |
|---|---|---|---|---|---|
| Logging / Audit | Append-only decision records (A8 fields), correlation IDs, guardrail outcomes, prompt/model/version metadata | `DecisionRecord`, decision log store/DDL, structured logs | Write errors surfaced/retried; never silently drop outcomes | REQ-X-LOG-001, REQ-F-RTE-002, REQ-F-VAL-002 | A8, A9 |
| Monitoring / Metrics | Volume, business, technical, governance metrics; latency/error/fallback/provider/guardrail counters; run reports | Harness/report outputs, metrics calculators | Code-calculated from run records; partial failures reported explicitly | REQ-X-MON-001, REQ-F-HAR-001, REQ-F-HAR-002, REQ-NF-PERF-001 | A9, A10 |
| Governance / Safety | Policy enforcement (no-doc/must-not-auto/sensitive), PII/secret hygiene, explainability, fairness/segment review hooks | `never_do` policies, guardrails, routing policy config, audit records | Policy-first deny/block/escalate; no unvalidated release | REQ-X-GOV-001, REQ-NF-SEC-001, REQ-NF-FAIR-001, REQ-NF-EXPL-001, REQ-NF-ACC-001 | A5, A7, A8, A11 |

## 3. Platform/supporting capabilities

| Capability | Responsibilities | REQ refs | A-criteria |
|---|---|---|---|
| LLM/Embedding provider abstraction & resilience | OpenRouter-first config, provider swap, retries/backoff, rate limiting, timeout, disk cache, degraded/offline simulation | REQ-F-OPS-001, REQ-NF-REL-001, REQ-NF-MAINT-001 | A11 |
| Unattended harness & evaluation outputs | `--input/--output`, process all tickets, no silent drops, code-calculated metrics report | REQ-F-HAR-001, REQ-F-HAR-002 | A9, A10 |
| Automated tests | Single documented test command; tests for core behaviors/regressions | REQ-F-TST-001 | A12 |
| Configuration & determinism | Env-driven config, prompt/model versioning, deterministic router, reproducible runs/caching | REQ-NF-EXPL-001, REQ-NF-MAINT-001, REQ-F-RTE-001 | A6, A11, A12 |

## 4. A1–A12 coverage summary

| Criterion | Primary components/concerns | REQs |
|---|---|---|
| A1 Ingest | Ingest | REQ-F-ING-001/002 |
| A2 Classify | Classify | REQ-F-CLS-001/002 |
| A3 Retrieve/Route | Retrieve, Route | REQ-F-RET-001/002, REQ-F-RTE-001/002 |
| A4 Generate (grounded/cited/structured) | Retrieve, Generate | REQ-F-RET-001/002, REQ-F-GEN-001/002 |
| A5 Validate/guardrails run | Validate, Governance | REQ-F-VAL-001/002, REQ-X-GOV-001 |
| A6 Calibration/thresholding/determinism | Route, Monitoring, NFR accuracy | REQ-F-RTE-001, REQ-NF-ACC-001, REQ-X-MON-001 |
| A7 Blocking guardrail evidence | Validate, Logging | REQ-F-VAL-001/002, REQ-X-LOG-001 |
| A8 Decision log | Logging/Audit | REQ-X-LOG-001 |
| A9 Unattended end-to-end harness/report | Harness, Monitoring, all pipeline | REQ-F-HAR-001/002, REQ-X-MON-001 |
| A10 Regression/metrics reproducibility | Harness, Tests, Monitoring | REQ-F-HAR-002, REQ-F-TST-001, REQ-X-MON-001 |
| A11 Failure handling | Provider resilience, all components fail-soft | REQ-F-OPS-001, REQ-NF-REL-001, REQ-F-ING-002, REQ-F-CLS-002, REQ-F-RET-002, REQ-F-GEN-002, REQ-F-VAL-002 |
| A12 Tests run with documented command | Tests/Maintainability | REQ-F-TST-001, REQ-NF-MAINT-001 |