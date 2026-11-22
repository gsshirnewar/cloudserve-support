# LLD — CloudServe Intelligent Support System (T10)

**Version:** 0.1 (draft)  
**Date:** 2026-11-22  
**Companion:** [HLD.md](HLD.md), [component_req_map.md](component_req_map.md), [../governance/decision_log_schema_draft.md](../governance/decision_log_schema_draft.md)

## 1. Module/package layout (target)
```text
src/
  api/            # FastAPI app and endpoints
  ingest/         # channel adapters + normalization
  classify/       # intent/urgency/confidence classifier
  retrieve/       # chunking, indexing, search, relevance filtering
  route/          # deterministic routing policy (pure function + config)
  generate/       # grounded answer/draft/summary generation
  validate/       # pre-release blocking guardrails
  store/          # decision log, cache, persistence adapters
  providers/      # LLM/embedding provider abstraction, retry/rate-limit/cache
  schemas/        # Pydantic models (shared contracts)
  pipeline/       # LangGraph state graph and orchestration
evaluation/
  harness.py      # unattended batch runner (--input, --output)
  metrics.py      # code-calculated metrics
tests/
```

## 2. Shared contracts (Pydantic schemas)
> Names are design targets; implementation may split modules but must preserve equivalent fields/behavior.

### 2.1 Ingest
**Input (`RawTicket`)**: source payload + metadata
- `source_channel: Literal["email","chat","docs_comment","forum"]`
- `raw_text: str | None`, `subject: str | None`, `body: str | None`
- `ticket_id: str | None`, `received_at: str | None`
- `customer: {customer_id?, name?, tier?, region?, language_fluency?}`
- `metadata: dict[str, Any]` (unrecognized fields preserved)

**Output (`NormalizedTicket`)**
- `ticket_id: str` (generated if missing)
- `channel: str`, `received_at: str | None`
- `subject: str`, `body: str`, `combined_text: str`
- `customer: {...}`, `raw_ref: str|dict` (original preserved), `ingest_warnings: list[str]`

**Failure behavior:** never crash; empty/missing/invalid fields normalized with warnings and safe defaults (REQ-F-ING-002).

### 2.2 Classify
**Input:** `NormalizedTicket`  
**Output (`ClassificationResult`)**
- `intent: str`, `urgency: str`
- `confidence: float` (0..1), `urgency_confidence: float | None`
- `alternatives: list[{intent, score|confidence}]` (top-k, not only chosen)
- `rationale: str | None`, `classifier_status: "ok"|"fallback"|"error"`, `error: str | None`

**Failure behavior:** on timeout/parse/provider failure return defined fallback (e.g. `intent="unknown"`, `urgency="unknown"`, low confidence, status fallback/error) and continue (REQ-F-CLS-002, A11).

### 2.3 Retrieve
**Input:** `NormalizedTicket`, `ClassificationResult` (and optional routing hints)  
**Output (`RetrievalResult`)**
- `query: str`, `hits: list[RetrievalHit]`, `top_score: float | None`
- `sufficient_evidence: bool`, `threshold: float`, `retrieval_status: "ok"|"no_hit"|"error"`

**`RetrievalHit`**
- `doc_id: str`, `chunk_id: str`, `title: str`, `category: str | None`
- `text: str`, `score: float`, `rank: int`
- `metadata: {applies_to?, related_docs?, last_reviewed_days_ago?, chunk_index?, source_path?}`

**Failure behavior:** index/search errors return `retrieval_status="error"` or `no_hit` with empty hits; below-threshold results filtered out (may yield no hits) (REQ-F-RET-002).

### 2.4 Route
**Input:** `ClassificationResult`, `RetrievalResult`, `PolicyConfig`/thresholds, ticket risk flags  
**Output (`RouteDecision`)**
- `action: Literal["auto_answer","assist_draft","escalate","block"]`
- `reason_code: str`, `reason_text: str` (manager-readable)
- `confidence: float`, `thresholds_used: dict`, `policy_flags: list[str]`
- `is_deterministic: true`, `requires_human: bool`

**Function contract (pure/deterministic):**
```text
route(classification, retrieval, thresholds, policy_flags, ticket_context) -> RouteDecision
```
- No I/O, no randomness, no clock dependence except optional explicit timestamp passed in if needed for logging outside the decision. Same inputs/config => same output (REQ-F-RTE-001, A3).

### 2.5 Generate
**Input:** `NormalizedTicket`, `ClassificationResult`, `RetrievalResult`, `RouteDecision`  
**Output (`GenerationResult`)**
- `mode: "answer"|"draft"|"escalation_summary"|"abstain"`
- `response_text: str`, `citations: list[{doc_id, chunk_id, claim_ref?}]`
- `structured: dict` (machine-parseable schema, e.g. answer/summary/unknowns/actions)
- `unknowns: list[str]`, `generation_status: "ok"|"fallback"|"error"`

**Failure behavior:** provider/parse failure returns abstain/escalation-ready fallback text/structure and status error; never fabricate citations (REQ-F-GEN-001/002).

### 2.6 Validate
**Input:** `GenerationResult` (or escalation draft), `NormalizedTicket`, `RetrievalResult`, `RouteDecision`  
**Output (`ValidationResult`)**
- `passed: bool`, `blocked: bool`, `action: "release"|"block"|"redact_and_release"|"escalate"`
- `checks: list[{name, passed, severity, details}]`
- `pii_detected: bool`, `unsupported_claims_detected: bool`
- `validator_status: "ok"|"error"`

**Failure behavior:** validator internal error defaults to safe outcome (block/escalate) and records error (fail-safe) (REQ-F-VAL-001/002).

### 2.7 Decision record (A8)
**Output (`DecisionRecord`)** persisted append-only per ticket/run (see §7 DDL). Includes run/ticket IDs, normalized input refs/hash, classification, retrieval/citations, route, generation summary, validation checks/actions, errors/fallbacks, model/prompt versions, timings.

## 3. LangGraph state and nodes
### 3.1 State (`PipelineState`, TypedDict/Pydantic model)
- `raw_ticket: dict`
- `ticket: NormalizedTicket | None`
- `classification: ClassificationResult | None`
- `retrieval: RetrievalResult | None`
- `route: RouteDecision | None`
- `generation: GenerationResult | None`
- `validation: ValidationResult | None`
- `outcome: Literal["answered","drafted","escalated","blocked","failed_soft"] | None`
- `errors: list[dict]`, `timings_ms: dict[str,int]`
- `config: dict` (thresholds/model/prompt versions, run metadata)
- `decision_record: dict | None`

### 3.2 Nodes
| Node | Reads | Writes | Notes |
|---|---|---|---|
| `ingest_node` | raw_ticket | ticket, errors, timings | channel normalization, preserve raw |
| `classify_node` | ticket | classification | fallback on failure; records alternatives |
| `retrieve_node` | ticket, classification | retrieval | thresholded, resolvable IDs |
| `route_node` | classification, retrieval, config/policy | route | **pure function call**; deterministic |
| `generate_node` | ticket, classification, retrieval, route | generation | answer/draft/summary/abstain modes |
| `validate_node` | generation, ticket, retrieval, route | validation, outcome | always before release; can block |
| `escalate_node` | ticket, classification, retrieval, route, generation/validation | generation(outcome package), outcome | builds escalation-with-context |
| `finalize_node` | all | decision_record, persisted log/metrics events | append-only write, no mutation of prior record |

### 3.3 Conditional edges
- After `route_node`: `auto_answer|assist_draft -> generate_node`, `escalate -> escalate_node` (no customer-facing generation required except escalation summary package as configured).
- After `validate_node`: `passed -> finalize(release)`, `blocked -> finalize(block/escalate)` or `escalate_node` depending on policy.
- Any node exception caught at orchestration boundary -> error recorded + fallback transition to safe outcome (`failed_soft`/escalate) + finalize.

## 4. Retrieval, chunking, and indexing
- **Corpus source:** `data/documentation.json` (fields: `doc_id,title,category,applies_to,content,related_docs,last_reviewed_days_ago`).
- **Chunking strategy (initial, ADR-002):** split `content` into ~300–600 char chunks (~75–150 tokens target) with 10–20% overlap; preserve paragraph/sentence boundaries when possible; create whole-doc chunk fallback for short articles.
- **Chunk metadata:** `doc_id, chunk_id, title, category, applies_to, related_docs, last_reviewed_days_ago, chunk_index, char_start/end`.
- **Embedding/index:** configurable embedding model (default local `all-MiniLM-L6-v2` per scaffold) and vector store (Chroma/local persistent path); interface allows swap without pipeline changes.
- **Search:** top-k retrieval + score normalization/threshold; return empty when `top_score < relevance_threshold` or no hits.
- **Citations:** generation and escalation outputs must reference resolvable `doc_id`/`chunk_id` present in retrieval results/corpus.

## 5. Provider abstraction and resilience
### 5.1 Interface
- `LLMProvider.generate(messages|prompt, model, params, response_schema?) -> ProviderResponse`
- `EmbeddingProvider.embed(texts, model) -> vectors`
- Common error types: `Timeout`, `RateLimited`, `Unavailable`, `AuthConfig`, `InvalidResponse`, `Unknown`.

### 5.2 Resilience controls
- **Disk cache:** key = hash(provider, model, prompt_version, rendered input/messages, params, schema id). Cache hit bypasses network.
- **Retries/backoff:** exponential backoff with jitter for retryable errors (429/5xx/timeouts) up to configured max attempts/time budget.
- **Rate limiting/concurrency:** token/bucket or semaphore limiter to avoid free-tier bursts; configurable per run.
- **Timeouts:** per-call timeout; bounded total node budget.
- **Degraded/offline mode:** simulation flag or detected outage returns typed degraded result (no exception leak) enabling A11 tests and safe continuation.
- **Provider swap:** config-driven (`LLM_PROVIDER`, base URL/model keys) with OpenRouter default; adapters isolate vendor specifics.

## 6. Guardrail design (pre-release, blocking)
| Guardrail | Method (v1 design) | Block condition | Output/evidence |
|---|---|---|---|
| PII/private data | Rule/pattern checks (email/phone/IDs/secrets) + optional LLM assist; redact-detection logic scoped to outbound content | Detected PII/secret in releasable response | `pii_detected`, check details, blocked/redacted action |
| Unsupported claims / grounding | Compare answer claims/citations against retrieved passages; require citations for factual claims; abstain if no evidence | Claims not supported by retrieved evidence or missing required citations | `unsupported_claims_detected`, support score/details |
| Policy/safety routing | Enforce must-not-auto/no-doc/sensitive intent rules (route/validate) | Auto-release attempted for restricted case | blocked/escalated with reason |
| Prompt-injection resistance | Input isolation (delimited data blocks), schema-constrained outputs, ignore customer instructions in content | N/A (preventive) + validation of format/policy adherence | parse/validation status, logged anomalies |
| Output integrity | Schema/parse validation, empty/unsafe response checks | Unparseable or unsafe output | fail-safe block/escalate |

**Execution rule:** `validate_node` runs on every generated/ready response before release in all modes (API, harness, tests) and records checks regardless of pass/block.

## 7. Decision log storage (DDL target, SQLite-compatible)
Aligned to [decision_log_schema_draft.md](../governance/decision_log_schema_draft.md); field names may be finalized in implementation but A8 minimums must be present.

```sql
CREATE TABLE IF NOT EXISTS decision_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  run_id TEXT NOT NULL,
  ticket_id TEXT NOT NULL,
  source_channel TEXT,
  input_hash TEXT,
  normalized_subject TEXT,
  normalized_body TEXT,
  intent TEXT,
  intent_confidence REAL,
  urgency TEXT,
  urgency_confidence REAL,
  alternatives_json TEXT,
  retrieval_status TEXT,
  top_score REAL,
  sufficient_evidence INTEGER,
  retrieved_doc_ids_json TEXT,
  citations_json TEXT,
  route_action TEXT,
  route_reason_code TEXT,
  route_reason_text TEXT,
  thresholds_json TEXT,
  generation_mode TEXT,
  response_text TEXT,
  validation_passed INTEGER,
  validation_blocked INTEGER,
  guardrail_checks_json TEXT,
  pii_detected INTEGER,
  unsupported_claims_detected INTEGER,
  final_outcome TEXT,
  error_flags_json TEXT,
  provider TEXT,
  model TEXT,
  prompt_versions_json TEXT,
  latency_ms_total INTEGER,
  latency_ms_by_node_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_decision_log_run_ticket ON decision_log(run_id, ticket_id);
CREATE INDEX IF NOT EXISTS idx_decision_log_outcome ON decision_log(final_outcome);
CREATE INDEX IF NOT EXISTS idx_decision_log_route ON decision_log(route_action);
```

**Integrity:** append-only writes (no updates/deletes in normal flow), one finalized record per ticket per run (or explicit event sequence correlated by run/ticket), PII-minimized stored text per policy.

## 8. Failure handling matrix (A11 + component failures)
| Component | No retrieval hit / insufficient evidence | Provider timeout / 5xx | Provider fully down / unavailable | Rate limiting (429) | Malformed/empty input | Other failure | User/batch impact |
|---|---|---|---|---|---|---|---|
| Ingest | N/A | N/A | N/A | N/A | Normalize with defaults/warnings; empty body allowed but flagged | Encoding/parse issues handled as warnings | No crash; ticket continues with `ingest_warnings` |
| Classify | N/A | Retry bounded; fallback classification (`unknown`, low confidence) | Degraded fallback classification | Backoff+jitter, cache; fallback if exhausted | Uses normalized empty-safe text; may lower confidence | Parse/schema error -> fallback | Continues to retrieval/route with uncertainty flags |
| Retrieve | Return empty hits, `sufficient_evidence=false` | N/A (local/index) unless embedding provider used -> retry/fallback | If embedding/provider unavailable, return `retrieval_status=error/no_hit` fallback | Backoff if remote embedding/rerank limited | Query built from safe normalized text | Index read error -> no_hit/error | Route to escalate/assist/abstain per policy |
| Route (pure) | Receives retrieval state and routes accordingly | N/A | N/A | N/A | Deterministic handling of missing/unknown fields | Invalid config -> safe default escalate + log | Deterministic safe decision |
| Generate | Must abstain/escalate; no fabricated answer | Retry bounded; fallback abstain/escalation summary | Degraded abstain/escalation response (template-based if needed) | Backoff+jitter, cache reuse | Prompt constructed from normalized fields; no crash | Unparseable output -> retry then fallback | No crash; structured fallback recorded |
| Validate | N/A | If LLM-assist validator unavailable, rule checks still run; fail-safe block/escalate on validator error | Fail-safe block/escalate (no unvalidated release) | Backoff for assist checks; prefer deterministic rules | Validates available fields safely | Validator exception -> block/escalate + error log | **Never release unvalidated output** |
| Pipeline/Harness | Counted as processed outcome | Record error and continue next ticket | Record outage and continue/degrade batch | Throttle and continue | Per-ticket failure isolated | Unexpected exception caught at boundary | Batch completes; no silent drops (A9/A11) |

## 9. Determinism, calibration, and configuration
- **LLM calls:** `temperature=0` (or provider-equivalent), fixed top_p/max tokens where supported, prompt/model versions recorded; response caching for reproducibility in dev/tests.
- **Router:** pure function of `(classification, retrieval, thresholds, policy_flags)`; thresholds stored in config/versioned artifact; no randomness/time/network.
- **Threshold derivation (method):** sweep confidence/retrieval thresholds on development data splits, evaluate precision/recall/escalation/hallucination trade-offs, select operating point, and document calibration (ECE/reliability curve) per eval plan (T11). v1 implements configurable thresholds; final values set from data.
- **Seeds:** set RNG seeds for any sampling components (if used) in indexing/eval; default pipeline path non-sampling.

## 10. Component interface summary (input/output/failure/REQs)
| Component | Input schema | Output schema | Failure behavior (summary) | REQ refs |
|---|---|---|---|---|
| Ingest | `RawTicket` | `NormalizedTicket` | Fail-soft normalization, warnings, no crash | REQ-F-ING-001/002 |
| Classify | `NormalizedTicket` | `ClassificationResult` | Fallback + alternatives on error/uncertainty | REQ-F-CLS-001/002 |
| Retrieve | `NormalizedTicket`, `ClassificationResult` | `RetrievalResult` | No-hit/thresholded empty/error fallback | REQ-F-RET-001/002 |
| Route | `ClassificationResult`, `RetrievalResult`, policy config | `RouteDecision` | Deterministic; safe default escalate on invalid state | REQ-F-RTE-001/002 |
| Generate | `NormalizedTicket`, `ClassificationResult`, `RetrievalResult`, `RouteDecision` | `GenerationResult` | Abstain/fallback on provider/parse failure; grounded/cited only | REQ-F-GEN-001/002 |
| Validate | `GenerationResult`, context | `ValidationResult` | Always-run; fail-safe block/escalate on errors | REQ-F-VAL-001/002 |
| Logging/Store | Pipeline events/`DecisionRecord` | Persisted log/metrics records | Append-only, retryable write with error surfacing | REQ-X-LOG-001 |
| Monitoring/Harness | Run inputs/config/results | Metrics/report artifacts | Code-calculated, complete accounting, no silent drops | REQ-X-MON-001, REQ-F-HAR-001/002 |
| Governance | Policies/config/check outcomes | Enforced decisions/blocks/audit evidence | Policy-first constraints (must-not-auto, no-doc, PII) | REQ-X-GOV-001 |

## 11. Testability hooks
- Provider simulation modes: force timeout/429/5xx/unavailable, disable network/cache-only.
- Deterministic fixtures for normalized tickets, retrieval hits, and route decisions.
- Harness accepts `--input/--output` and emits per-ticket outcomes + aggregate metrics for reconciliation.
- Decision log queryable for A8/A9 reconciliation and guardrail activation counts.