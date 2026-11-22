# Test Plan (T11) — A1–A12 to Pytest Mapping

**Version:** 0.1 (draft)  
**Date:** 2026-11-22  
**Companion:** [eval_plan.md](eval_plan.md), [HLD.md](HLD.md), [LLD.md](LLD.md), [../prd/PRD_v1.md](../prd/PRD_v1.md)  
**Command (target):** `python -m pytest tests/ -v` (single documented command per README/A12)

## 1. Test strategy
- **Unit tests:** component logic (ingest normalization, routing function, guardrail rules, schema validation, metrics calculations).
- **Integration tests:** pipeline node interactions, provider abstraction with mocks/cache, retrieval/index query contracts, decision-log writes.
- **End-to-end tests:** harness/API flows on fixtures/small datasets with deterministic/mocked providers where needed.
- **Failure-injection tests:** A11 conditions (timeout, 429, outage/provider fully down, malformed input, no retrieval hit) using simulated provider modes/fakes.
- **Governance tests:** pre-release guardrail execution/blocking, PII detection/redaction, decision-log completeness/reconciliation.
- **Regression tests:** frozen fixtures and metric snapshots for critical behaviors (A10 workflow to be implemented alongside harness).

**Determinism controls:** fixed seeds, `temperature=0`, cached/mocked LLM responses for tests, pure router function tests with explicit inputs/thresholds.

## 2. A1–A12 acceptance criteria → named tests

| A# | Acceptance criterion | Test level | Named test(s) (planned) | Evidence / assertion |
|---|---|---|---|---|
| A1 | Ingest accepts tickets from all 4 channels and normalizes to one representation; preserves original text/channel; handles missing fields/unusual chars/empty bodies without failing | Unit + integration | `tests/test_ingest_a1.py::test_ingest_normalizes_email_ticket`<br>`tests/test_ingest_a1.py::test_ingest_normalizes_chat_ticket`<br>`tests/test_ingest_a1.py::test_ingest_normalizes_docs_comment_ticket`<br>`tests/test_ingest_a1.py::test_ingest_normalizes_forum_ticket`<br>`tests/test_ingest_a1.py::test_ingest_preserves_raw_text_and_channel`<br>`tests/test_ingest_a1.py::test_ingest_handles_missing_fields_and_empty_body`<br>`tests/test_ingest_a1.py::test_ingest_handles_unicode_and_long_body` | Normalized schema fields present; raw preserved; no exception on edge inputs |
| A2 | Classify assigns intent + urgency with numeric confidence; returns defined fallback on failure; records alternatives considered | Unit + integration | `tests/test_classify_a2.py::test_classify_returns_intent_urgency_confidence`<br>`tests/test_classify_a2.py::test_classify_returns_alternatives_not_only_top_choice`<br>`tests/test_classify_a2.py::test_classify_provider_failure_returns_fallback_no_exception`<br>`tests/test_classify_a2.py::test_classify_low_confidence_marks_uncertainty` | Output schema valid; fallback status/values on induced failure; alternatives list populated |
| A3 | Retrieve returns ranked passages with scores and resolvable corpus IDs; applies relevance threshold (returns nothing if irrelevant). Route decides auto/escalate (or assist) using data-determined threshold, deterministic same-input same-decision, records manager-readable reason; escalations carry summary and retrieved sources | Unit + integration | `tests/test_retrieve_a3.py::test_retrieve_returns_ranked_hits_with_scores_and_doc_ids`<br>`tests/test_retrieve_a3.py::test_retrieve_below_threshold_returns_no_hits`<br>`tests/test_route_a3.py::test_route_is_deterministic_pure_function`<br>`tests/test_route_a3.py::test_route_records_manager_readable_reason`<br>`tests/test_route_a3.py::test_route_escalation_includes_summary_and_sources` | Resolvable `doc_id/chunk_id`; empty on no-hit/low score; repeated calls identical; escalation payload contains required context |
| A4 | Generate produces grounded answer with citations; states plainly when unknown; separates ticket content from instructions; outputs defined parseable structure | Unit + integration | `tests/test_generate_a4.py::test_generate_returns_grounded_cited_structured_answer`<br>`tests/test_generate_a4.py::test_generate_abstains_when_evidence_insufficient`<br>`tests/test_generate_a4.py::test_generate_prompt_injection_does_not_override_instructions`<br>`tests/test_generate_a4.py::test_generate_output_is_machine_parseable` | Citations reference retrieved docs; abstain/unknown path on no evidence; injection fixture ignored; schema parse succeeds |
| A5 | Validate runs on every generated response before release; checks at minimum PII/private data and unsupported claims; can block; records checks/findings for pass/block | Unit + integration | `tests/test_validate_a5.py::test_validate_runs_before_release_for_every_response`<br>`tests/test_validate_a5.py::test_validate_detects_pii_and_can_block`<br>`tests/test_validate_a5.py::test_validate_detects_unsupported_claims_and_can_block`<br>`tests/test_validate_a5.py::test_validate_records_checks_and_findings_on_pass_and_block` | Validator invoked in pipeline path; blocking outcomes set; audit fields populated |
| A6 | Confidence/thresholding/calibration behavior evidenced (deterministic threshold application; calibration-ready metrics hooks) | Unit + evaluation harness tests | `tests/test_route_a3.py::test_route_applies_configured_thresholds_deterministically`<br>`tests/test_eval_a6.py::test_calibration_ece_and_reliability_bins_computation`<br>`tests/test_eval_a6.py::test_threshold_sweep_outputs_tradeoff_metrics` | Threshold config drives decision; ECE/binning functions correct on fixtures; sweep artifact schema valid |
| A7 | At least one blocking guardrail demonstrated with evidence | Integration/demo fixture test | `tests/test_validate_a5.py::test_blocking_guardrail_prevents_release_and_logs_evidence`<br>`tests/test_harness_a9.py::test_harness_report_counts_blocked_by_guardrails` | Crafted trigger results in blocked/non-released outcome and recorded guardrail activation |
| A8 | Every decision logged with required fields (input, prediction, confidence, sources, action, reason) and reconcilable | Integration + harness | `tests/test_logging_a8.py::test_decision_log_written_for_each_processed_ticket`<br>`tests/test_logging_a8.py::test_decision_log_contains_required_a8_fields`<br>`tests/test_logging_a8.py::test_decision_log_reconciles_with_harness_outcomes` | One record per ticket/run outcome; required fields non-null where applicable; counts match report |
| A9 | Single documented command runs unattended end-to-end on input path, processes all tickets, no silent drops, produces metrics report without manual work | End-to-end harness | `tests/test_harness_a9.py::test_harness_cli_accepts_input_output_args`<br>`tests/test_harness_a9.py::test_harness_processes_all_tickets_unattended_no_silent_drops`<br>`tests/test_harness_a9.py::test_harness_produces_required_metrics_report`<br>`tests/test_harness_a9.py::test_harness_works_with_arbitrary_input_path` | CLI args accepted; `processed == input_count`; every ticket answered/escalated/blocked/failed-soft logged; report includes Spec §04 groups |
| A10 | Regression/baseline comparison supported (metrics reproducible and comparable across runs) | Integration + harness | `tests/test_eval_a10.py::test_metrics_calculations_match_known_fixture_baseline`<br>`tests/test_eval_a10.py::test_run_manifest_captures_versions_config_and_dataset_identity`<br>`tests/test_eval_a10.py::test_repeated_run_on_same_cached_fixture_is_reproducible` | Deterministic fixture metrics stable; manifest fields present; baseline comparison artifact generated |
| A11 | Handles failure without crashing: no retrieval hit, provider timeout/outage, rate limiting, malformed input (including provider fully down) | Failure-injection | `tests/test_resilience_a11.py::test_no_retrieval_hit_degrades_without_crash`<br>`tests/test_resilience_a11.py::test_provider_timeout_degrades_and_continues`<br>`tests/test_resilience_a11.py::test_provider_fully_down_degrades_and_continues_batch`<br>`tests/test_resilience_a11.py::test_provider_rate_limit_429_retries_then_degrades`<br>`tests/test_resilience_a11.py::test_malformed_input_handled_without_crash`<br>`tests/test_resilience_a11.py::test_batch_continues_after_induced_failures_no_silent_drop` | Typed degraded/fallback outcomes; batch completes; all failures logged |
| A12 | Tests run with a single documented command and pass | Meta/process + CI-local | `tests/test_smoke_a12.py::test_pytest_suite_entrypoint_collects`<br>`tests/test_harness_a9.py::test_harness_help_documents_input_output`<br>*(process)* README command `python -m pytest tests/ -v` executed successfully | Collection/execution works in clean env; help/docs present; CI/local command passes |

## 3. Spec §04 metrics report coverage tests

| Report group | Required figures | Test(s) |
|---|---|---|
| Volume | Tickets processed, answered automatically, escalated, blocked by guardrails | `tests/test_harness_a9.py::test_harness_produces_required_metrics_report` |
| Business | FCR, mean and median response time, escalation rate | `tests/test_eval_metrics.py::test_business_metrics_fcr_mean_median_latency_escalation_rate` |
| Technical | Classification precision and recall per class, retrieval hit rate, latency p50/p95 | `tests/test_eval_metrics.py::test_technical_metrics_precision_recall_hit_rate_latency_percentiles` |
| Governance | Decisions logged, guardrail activations by type, any private data detections | `tests/test_eval_metrics.py::test_governance_metrics_logged_guardrails_pii_detections` |

## 4. Additional planned test suites (non-A numbered but required by plan/PRD)

| Area | Named tests (planned) | Purpose |
|---|---|---|
| Provider abstraction/cache | `tests/test_provider.py::test_cache_hit_avoids_network_on_identical_call`<br>`tests/test_provider.py::test_retry_backoff_on_429_then_success`<br>`tests/test_provider.py::test_rate_limiter_handles_burst_without_crash` | Resilience/cost controls (supports A11, PRD REQ-F-OPS-001) |
| Retrieval/chunking | `tests/test_retrieval_index.py::test_chunking_preserves_metadata_and_doc_ids`<br>`tests/test_retrieval_index.py::test_citations_resolve_to_corpus` | Grounding/citation integrity (supports A4/A3) |
| Policy boundaries | `tests/test_route_policy.py::test_must_not_auto_intents_are_not_auto_released`<br>`tests/test_route_policy.py::test_no_doc_intents_feature_request_unclear_request_escalate_or_abstain` | Governance constraints (EV-37/EV-38, REQ-X-GOV-001) |
| Fairness/segmentation reporting | `tests/test_eval_fairness.py::test_segment_gap_calculation_by_fluency_tier_region` | <5pp gap computation and reporting hooks (PRD REQ-NF-FAIR-001) |
| API (if implemented) | `tests/test_api.py::test_submit_ticket_returns_structured_outcome`<br>`tests/test_api.py::test_health_endpoint` | Interface contract (supports demo/A1–A5 path) |

## 5. Fixtures and test data
- **Synthetic fixtures:** minimal tickets per channel, malformed/empty/unicode/oversized bodies, injection strings, PII samples, unsupported-claim prompts, no-hit queries.
- **Golden fixtures:** small labeled subset derived from development schema (not validation set) for deterministic metric and routing tests.
- **Provider fakes/simulators:** mock LLM/embedding clients with modes `ok`, `timeout`, `rate_limit`, `server_error`, `unavailable`, `malformed_response`.
- **No validation leakage:** `data/validation_tickets.json` excluded from automated test fixtures; tests requiring dataset paths use generated fixtures or dev-derived samples only.

## 6. Execution, environments, and reporting
- **Local:** `python -m pytest tests/ -v` (and optional markers e.g. `-m "not slow"` for quick loop).
- **Harness smoke:** `python -m evaluation.harness --help` and fixture run to temp output directory.
- **CI (planned):** lint/format (optional), unit/integration tests, secret scan; provider-dependent E2E tests run in mocked/cached mode.
- **Artifacts:** JUnit/XML or console report, coverage (optional), generated metrics report samples for harness tests.

## 7. Entry/exit criteria
| Phase | Entry | Exit |
|---|---|---|
| Component implementation (T14–T20) | Schema/LLD agreed | Relevant A1–A7 unit/integration tests passing with mocks/fakes |
| Integration & harness (T21–T25) | Components wired | A8–A11 tests passing on fixtures; unattended run on dev sample completes |
| Pre-submission | Frozen config/prompts/thresholds | A12 command passes; regression checks (A10) stable; one validation run executed and logged per protocol |

## 8. Open items (to finalize during implementation)
- Final pytest module names may be adjusted to match package layout, but **A1–A12 coverage and named-test intent must remain traceable** (update this plan if renamed).
- Exact "correct/grounded" adjudication rubric and judge prompt versions to be registered in prompt library (T13).
- Calibration metric reporting format (ECE vs bin-gap) to be fixed in metrics module; both computed where possible.