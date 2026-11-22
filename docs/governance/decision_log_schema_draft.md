# Decision Log Schema Draft (T02)

**Status:** Draft (seed for design/build). To be finalized when storage layer (`src/store`) is implemented.  
**Traces to:** Build Spec A8, Project Brief §07 (governance conditions), §08 (risk/governance obligations), plan task T02.

## Purpose
Record every automated decision so it is reconstructable months later. A8 requires: decisions counted against tickets processed must reconcile, and each decision must capture at minimum **input, prediction, confidence, sources, action, reason** (plus required operational fields implied by the spec/eval).

## Minimum field coverage (A8 mapping)
| A8 required element | Schema field(s) |
|---|---|
| Input | `ticket_id`, `channel`, `received_at`, `input_text_raw`, `input_text_normalized`, `input_hash`, `input_metadata_json` |
| Prediction | `predicted_intent`, `predicted_urgency`, `classification_alternatives_json`, `retrieval_query`, `retrieval_results_json` |
| Confidence | `intent_confidence`, `urgency_confidence`, `overall_confidence`, `confidence_method`, `threshold_used` |
| Sources | `retrieved_source_ids_json`, `retrieved_passages_json`, `citation_ids_json`, `corpus_version` |
| Action | `route_decision` (`auto_answer`/`escalate`/`block`/`fallback`), `final_action`, `response_sent`, `escalation_payload_json`, `guardrail_action` |
| Reason | `route_reason_text`, `guardrail_reason_text`, `fallback_reason_text`, `operator_readable_summary` |

## Proposed table: `decision_log`
One row per processed ticket/decision event (append-only in normal operation). If a ticket is retried, store a new row with incremented `attempt_no` and link via `run_id`/`ticket_id`.

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | INTEGER PK / UUID | Yes | Unique log record id. |
| `run_id` | TEXT | Yes | Evaluation/run identifier (batch/harness invocation) for reconciliation. |
| `ticket_id` | TEXT | Yes | Source ticket identifier from input dataset. |
| `attempt_no` | INTEGER | Yes | Retry attempt (1 = first). |
| `processed_at` | TEXT (ISO-8601 UTC) | Yes | When decision completed/logged. |
| `received_at` | TEXT | If available | Original ticket timestamp from input. |
| `channel` | TEXT | Yes | `email` \| `live_chat` \| `doc_comment` \| `forum` (normalized). |
| `input_text_raw` | TEXT | Yes | Original ticket text/body as received (subject to redaction policy if needed; prefer hashed/ref where sensitive). |
| `input_text_normalized` | TEXT | Yes | Normalized internal representation used downstream. |
| `input_hash` | TEXT | Yes | Hash of canonical input for dedupe/determinism checks. |
| `input_metadata_json` | TEXT (JSON) | Yes | Preserved channel fields, customer/tier/region/language fluency if present, missing-field flags. |
| `predicted_intent` | TEXT | Yes | Final intent label (or `unknown_fallback`). |
| `predicted_urgency` | TEXT | Yes | Final urgency label (or fallback). |
| `intent_confidence` | REAL | Yes | Numeric confidence in [0,1]. |
| `urgency_confidence` | REAL | Yes | Numeric confidence in [0,1]. |
| `overall_confidence` | REAL | Yes | Confidence used for routing/guarding (define method). |
| `confidence_method` | TEXT | Yes | How confidence was computed/calibrated. |
| `classification_alternatives_json` | TEXT (JSON) | Yes | Considered alternatives with scores/probabilities. |
| `retrieval_query` | TEXT | Yes | Query/queries issued to retriever. |
| `retrieval_results_json` | TEXT (JSON) | Yes | Ranked passages with source IDs, chunk IDs, scores, relevance decision. |
| `retrieved_source_ids_json` | TEXT (JSON) | Yes | Identifiable corpus source references for citations/audit. |
| `retrieved_passages_json` | TEXT (JSON) | Yes | Passage text/snippets or stable references used for grounding. |
| `citation_ids_json` | TEXT (JSON) | Yes | Citations attached to generated answer (or empty with reason). |
| `corpus_version` | TEXT | Yes | Documentation corpus identifier/hash/version. |
| `route_decision` | TEXT | Yes | `auto_answer` \| `escalate` \| `block` \| `fallback`. |
| `threshold_used` | REAL | Yes | Routing/confidence threshold applied. |
| `route_reason_text` | TEXT | Yes | Human-readable reason (support-manager readable). |
| `generated_answer_draft` | TEXT | No | Draft before validation (if produced). |
| `generated_answer_final` | TEXT | No | Final answer sent/escalation summary (if any). |
| `response_sent` | INTEGER/BOOLEAN | Yes | Whether an answer was released to user. |
| `final_action` | TEXT | Yes | Concrete outcome: `sent`, `escalated`, `blocked`, `failed_safe`, etc. |
| `guardrail_checks_json` | TEXT (JSON) | Yes | Checks run (PII, unsupported claims, tone, prompt-injection signals, etc.) and outcomes. |
| `guardrail_action` | TEXT | Yes | `none` \| `warned` \| `blocked` \| `redacted` (block must be possible per A7). |
| `guardrail_reason_text` | TEXT | Yes | What was checked/found, even if not blocked. |
| `escalation_payload_json` | TEXT (JSON) | No | Summary, retrieved sources, uncertainty/reason carried to human agent. |
| `fallback_reason_text` | TEXT | No | Provider timeout/outage, no retrieval hit, malformed input, rate limit, parse failure, etc. |
| `error_flags_json` | TEXT (JSON) | Yes | Structured error/degradation flags for A11 analysis. |
| `operator_readable_summary` | TEXT | Yes | One-line summary suitable for audit/review. |
| `model_provider` | TEXT | Yes | e.g. `openrouter` / `groq` / `local`. |
| `model_name` | TEXT | Yes | Model identifier used (or `n/a` in offline fallback). |
| `prompt_versions_json` | TEXT (JSON) | Yes | Prompt IDs/versions for classify/retrieve/generate/validate steps. |
| `code_version` | TEXT | No | Git commit/hash or build identifier if available. |
| `latency_ms_total` | INTEGER | Yes | End-to-end processing time for ticket. |
| `latency_breakdown_json` | TEXT (JSON) | No | Per-stage timings (ingest/classify/retrieve/generate/validate). |
| `determinism_key` | TEXT | No | Inputs/seed/config hash to support A5 same-input-same-decision checks. |

## Reconciliation & integrity requirements
- **A8:** `count(decision_log rows for run_id, successful terminal decisions)` must reconcile with tickets processed in harness output; no silent drops.
- **A9:** Every ticket in an unattended run produces either a sent answer or a logged escalation/block/failure outcome row.
- **Immutability:** Prefer append-only records; corrections via follow-up events/attempt rows, not in-place mutation of history.
- **No secrets:** Never log API keys or raw credentials; redact/tokenize detected private data in stored outbound text as required by policy.

## Open decisions (to resolve in implementation/design)
- Store full raw text vs redacted/raw+hash only (balance auditability with PII governance).
- SQLite schema normalization (single table vs `runs`, `tickets`, `retrieval_hits`, `guardrail_events` tables).
- How to represent "same input" determinism key under nondeterministic model outputs (routing determinism may depend on cached classification/retrieval artifacts).
- Corpus/prompt versioning source of truth.

## Validation checklist before implementation freeze
- [ ] All A8 minimum elements mapped to concrete fields.
- [ ] Harness can join/aggregate by `run_id` and `ticket_id`.
- [ ] Guardrail outcomes and actions are queryable for metrics report (A10/governance).
- [ ] Schema supports escalation payload with summary + retrieved sources + uncertainty (routing requirement).
- [ ] Schema supports fallback/error reasons for A11 conditions.
