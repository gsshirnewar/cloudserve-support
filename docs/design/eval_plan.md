# Evaluation Plan (T11)

**Version:** 0.1 (draft)  
**Date:** 2026-11-22  
**Depends on:** PRD v1, HLD/LLD, Stage 1 evidence (EV-29–EV-39)  
**Policy:** **Development data only** for design/tuning/thresholding; **`data/validation_tickets.json` reserved for one final evaluation run** (date + run count logged). Hidden assessment set not used.

## 1. Objectives
- Measure system behavior against business, technical, and governance targets (A9/A10, PRD §9).
- Support data-informed threshold selection and calibration (A6) without leakage from validation/hidden sets.
- Detect grounding/safety/fairness issues (hallucination, citation errors, PII leaks, segment gaps).
- Produce reproducible, code-calculated reports comparable to Stage 1 baselines.

## 2. Data splits and usage protocol

| Split | Source | Allowed use | Forbidden use |
|---|---|---|---|
| Development set | `data/development_tickets.json` (500) | EDA, prompt/component iteration, threshold sweeps, calibration, cross-validation, error analysis | Final acceptance claims without held-out protocol |
| Dev train/dev holdout (internal) | Derived from development set via stratified splits or CV folds (by intent/urgency/channel and outcome labels as appropriate) | Model/prompt/threshold tuning and selection; estimate generalization on dev distribution | Using validation labels/tickets |
| Validation set | `data/validation_tickets.json` (80) | **One final run only** after freeze (code/config/prompts/thresholds) | Any tuning, prompt iteration, threshold selection, debugging-driven re-runs except documented incident handling |
| Hidden assessment set | Not distributed | Instructor/final assessment only | Any access/use |

**Validation run protocol (mandatory):**
1. Freeze commit/tag, config, prompt versions, thresholds, and environment details.
2. Record pre-run metadata: date/time, operator, git commit/tag, command, `--input` path, `--output` path, provider/model config (no secrets), cache state.
3. Execute exactly **one** unattended final validation run: `python -m evaluation.harness --input data/validation_tickets.json --output evaluation/results/<run_id>/`
4. Log **run count = 1** for validation in run manifest and report; if a rerun is unavoidable (infrastructure failure before completion), document cause, timestamp, and exclude partial outputs from claims.
5. Do not modify thresholds/prompts based on validation outcomes except in a new development cycle (future version).

## 3. Metrics (definitions and formulae)

### 3.1 Spec §04 metrics report table (required)

| Group | Metric | Definition / formula | Source / notes |
|---|---|---|---|
| Volume | Tickets processed | `N_processed = count(tickets with terminal outcome)`; must equal input count in successful complete run | Harness outcome log |
| Volume | Answered automatically | `N_auto = count(outcome in {answered, auto_answer_released})` (final taxonomy fixed in implementation) | Decision log/harness |
| Volume | Escalated | `N_escalated = count(outcome == escalated)` including policy/risk/low-confidence/insufficient-evidence escalations | Decision log |
| Volume | Blocked by guardrails | `N_blocked = count(outcome == blocked OR validation.blocked == true)` | Validation/decision log |
| Business | First contact resolution (FCR) | **System/run proxy:** `FCR = N_resolved_first_contact / N_processed` where resolution is defined by evaluation rubric (e.g. correct grounded answer released without escalation/block requiring human rework). **Baseline derivation (dev history):** `FCR_hist = mean(history.first_contact_resolution)` over comparable subset. | Report both proxy definition and baseline comparison; do not conflate unless justified |
| Business | Mean response time | `mean_latency_s = (1/N_timed) * Σ latency_i` for timed responses (define scope: end-to-end pipeline or response generation path; report both if available) | Timestamps/latency fields |
| Business | Median response time | `median(latency_i)` over same scope as mean | Robust central tendency |
| Business | Escalation rate | `Escalation_rate = N_escalated / N_processed` | Decision log |
| Technical | Classification precision per class | For each intent/urgency class `c`: `Precision_c = TP_c / (TP_c + FP_c)` (0 if denominator 0; report support) | Predicted vs reference labels (dev/eval labels where available) |
| Technical | Classification recall per class | For each class `c`: `Recall_c = TP_c / (TP_c + FN_c)` | Per-class support required |
| Technical | Retrieval hit rate | `Retrieval_hit_rate = N_sufficient_retrieval / N_processed` where sufficient = `retrieval.sufficient_evidence == true` or `top_score >= threshold` and ≥1 relevant hit returned | Retrieval logs |
| Technical | Latency at median and 95th percentile | `p50_latency = percentile(latency_i, 50)`, `p95_latency = percentile(latency_i, 95)` | End-to-end and/or component latencies as instrumented |
| Governance | Decisions logged | `N_logged = count(decision_log records)`; integrity: `N_logged == N_processed` and unique ticket/run mapping | Decision store reconciliation |
| Governance | Guardrail activations by type | `Activations_t = count(checks where type==t and triggered==true)` for PII, unsupported_claims, policy/no-doc/sensitive, format/injection, etc. | Validation records |
| Governance | Any private data detections | `PII_detections = count(responses/checks with pii_detected==true)`; target **0 released** PII incidents | Must be highlighted; any >0 is critical |

### 3.2 Additional PRD/brief targets (defined for evaluation)

| Metric | Formula / method | Target |
|---|---|---|
| Hallucination rate (ungrounded/unsupported) | `Hallucination_rate = N_unsupported_or_fabricated / N_answered_or_drafted_evaluated` using groundedness rubric (judge + rules + spot-check adjudication) | ≤ 5% |
| Citation accuracy | `Citation_accuracy = N_claims_or_answers_with_valid_citations / N_claims_or_answers_requiring_citation` where valid citation resolves to retrieved/corpus passage supporting claim | ≥ 95% |
| Calibration (confidence vs correctness) | Reliability curve bins by predicted confidence; `ECE = Σ_b (n_b/N) * |acc(b) - conf(b)|`; also report max bin gap | Within 5 pp (ECE or stated calibration gap per agreed definition) |
| Availability / resilience behavior | `Run_completion_rate = completed_runs / attempted_runs` and per-ticket graceful handling rate under induced failures; report provider errors/timeouts/429 handled without crash | ≥ 99.5% target behavior/design intent (contextualized for free-tier) |
| Quality gap across customer groups | For metric `M` across groups `g` (language_fluency, tier, region): `Gap_M = max_g(M_g) - min_g(M_g)` on comparable/support-filtered subsets | < 5 pp for key quality outcomes |
| First reply time goal (product) | `first_reply_latency` from intake to first system response event (if instrumented) | < 5 minutes (target) |

## 4. Calibration and thresholding

### 4.1 Calibration method
- **Inputs:** predicted confidences (classification and/or answer/routing confidence proxies) and correctness labels/outcomes on dev holdout/CV folds.
- **Reliability curve:** bin predictions (e.g. 10 bins [0,0.1)…(0.9,1.0]); plot/compute mean confidence vs empirical accuracy per bin.
- **ECE:** `ECE = Σ_{b=1}^{B} (|S_b|/n) |acc(S_b) - conf(S_b)|`.
- **Diagnostics:** over/under-confidence by class/segment, abstention rates, confusion near thresholds.

### 4.2 Threshold sweep protocol
- **Parameters:** `route_auto_min_conf`, `route_assist_min_conf`, `retrieval_relevance_threshold`, `min_citations_or_support_score`, policy flags for must-not-auto intents.
- **Procedure:** grid/random sweep on dev CV folds; for each setting compute precision/recall (classification), retrieval hit rate, auto-answer rate, escalation rate, hallucination/unsupported rate, blocked rate, latency impact.
- **Selection:** choose operating point maximizing safe automation utility subject to constraints (PII released = 0, hallucination ≤ target, escalation/abstention for restricted cases, calibration within tolerance where feasible).
- **Determinism:** router remains pure function of (classification, retrieval, thresholds, policy flags).
- **Documentation:** store sweep config/results artifact (`evaluation/results/threshold_sweep.*`) with chosen thresholds and rationale.

## 5. Groundedness, hallucination, and citation accuracy evaluation

| Layer | Method | Purpose |
|---|---|---|
| Rule checks (automated) | Citation presence/format, cited `doc_id/chunk_id` resolves to corpus/retrieval, claim-support heuristics (overlap/entailment proxy as available), detection of unsupported definitive statements when retrieval insufficient | Fast, reproducible screening and blocking signals |
| Judge prompt (LLM-assisted, dev only with controls) | Structured rubric prompt comparing answer vs retrieved passages/ticket: supported / partially supported / unsupported / contradicted; requires cited evidence spans/IDs | Scalable semantic assessment; versioned prompt in registry |
| Manual spot-check sample | Human adjudication on stratified sample (by intent, channel, action, confidence bin; include escalations/blocks/auto answers); resolve disagreements and calibrate judge/rules | Gold/reference quality check and error analysis |

**Sampling guidance:** minimum stratified sample per evaluation cycle (e.g. 50–100 dev outputs for iteration, larger for milestone reviews) with oversampling of low-confidence, no-hit, blocked, and sensitive-intent cases; record sample IDs and adjudication notes.

## 6. Fairness audit method

| Dimension | Groups | Metrics | Method / sample considerations |
|---|---|---|---|
| Language fluency | `fluent`, `non_fluent` (as labeled) | FCR/proxy, escalation, block/abstain, hallucination/unsupported, citation accuracy, latency, CSAT proxy where applicable | Stratified reporting on dev; require minimum support per group before strong claims; report confidence/caveats |
| Customer tier | all tiers present (e.g. free/business/enterprise) | Same outcome/quality metrics | Compare gaps; ensure policy does not create unjustified service degradation |
| Region | all regions present | Same outcome/quality metrics | Monitor for retrieval/language/performance disparities |
| Channel | chat/email/forum/docs_comment | Operational/quality metrics | Not a protected attribute but important for parity and routing behavior |

**Gap calculation:** `max(group)-min(group)` for selected key metrics; flag if ≥5 pp and investigate causes (data, retrieval, policy, thresholds). **Caveat:** dev labels/segments are observational; avoid causal claims.

## 7. Business-metric derivation vs `history` baseline

| Metric | Dev `history` baseline (T04) | System evaluation metric | Comparability notes |
|---|---|---|---|
| FCR | `history.first_contact_resolution` mean/rate | Task-defined resolved-without-rework/appropriate outcome proxy | Definitions may differ; report mapping assumptions |
| Escalation | `history.escalated` mean/rate | `route/action == escalate` or final escalated outcome | Policy-driven escalations (safety/no-doc) may increase appropriately vs unsafe auto-answers |
| Repeat contact | `history.repeat_contact` | Proxy only if available in evaluation labels/simulation; otherwise track follow-up-needed/abstain signals | Not directly observable in single-run harness unless labeled |
| CSAT | `history.csat_rating` mean/median | Not directly produced by harness; use quality proxies and sampled review | Treat as benchmark context, not automatic run output |
| Resolution/response time | `history.resolution_time_minutes` (resolution duration) | Pipeline/response latency (ms/s) and first-reply proxy | **Different constructs**; brief cites 8–12h first reply baseline separately |

## 8. Reproducibility and artifacts
- Code-calculated metrics only (no manual spreadsheet totals for reported values).
- Persist per-run manifest: timestamp, git commit, config/prompt/model versions, dataset path/hash, thresholds, cache mode, command, environment summary.
- Save raw per-ticket outputs/decision records and aggregate report (`json/csv/md`).
- For validation: include explicit statement `validation_used_once=true`, `validation_run_count=1`, and run date.

## 9. Risks and limitations
- Label noise/proxy labels in dev data may bias thresholds; mitigate with spot checks and sensitivity analysis.
- LLM judge variability; mitigate with versioned prompts, low temperature, and human adjudication sample.
- Provider non-determinism/latency variance on free tier; mitigate with caching, fixed params, and reporting conditions.
- Segment sample sizes may be small; report support counts and avoid over-interpretation.