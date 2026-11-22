# PRD v1 — CloudServe Intelligent Support System (Stage 2)

## 1. Document control

| Field | Value |
|---|---|
| Document ID | PRD-CloudServe-v1 |
| Version | 1.0 (draft for Phase C start) |
| Date | 2026-11-22 |
| Owner | Capstone delivery (CloudServe support AI project) |
| Status | Draft v1 (seed for design/build/traceability) |
| Scope baseline | Stage 1 discovery artifacts T03–T08; Project Brief; Build Specification A1–A12 |
| Key inputs | [../workbooks/stage1_workbook.md](../workbooks/stage1_workbook.md), [../workbooks/stage1_problem_statement.md](../workbooks/stage1_problem_statement.md), [../workbooks/stage1_agent_time_success_constraints.md](../workbooks/stage1_agent_time_success_constraints.md), [../workbooks/evidence_register_complete.csv](../workbooks/evidence_register_complete.csv) |
| Related artifacts | [../governance/decision_log_schema_draft.md](../governance/decision_log_schema_draft.md), [../governance/never_do.md](../governance/never_do.md), [traceability.csv](traceability.csv) |
| Validation data policy | Development data used for discovery/design; **validation/hidden assessment tickets not opened or tuned on** |

## 2. Problem statement

CloudServe’s support operation is failing to deliver timely, reliable first-contact help because existing curated KB answers are not consistently found, applied, and delivered with confidence at the point of need. In the development set (n=500), 71.4% of tickets are labeled `answerable_from_docs` and 62.2% `expected_auto_respond`, yet baselines remain weak (FCR 43.8%, escalation 56.2%, repeat contact 21.6%, CSAT mean 2.972). Doc-answerable and expected-auto tickets still show escalation/repeat-contact gaps, indicating a delivery/grounding/confidence/routing problem rather than missing knowledge alone.

**Framing:** not a generic “chatbot”, but an evidence-grounded support decision-and-assistance system that triages, retrieves, cites, drafts/assists or auto-resolves only within policy/confidence boundaries, escalates with context, and logs auditable decisions/guardrail outcomes.  
**Primary evidence:** EV-01, EV-03, EV-04, EV-05, EV-08–EV-26, EV-29–EV-39 (see Stage 1 artifacts and evidence register).

## 3. User groups

| User group | Goals / needs | Pain points (current) | Success from system | Evidence |
|---|---|---|---|---|
| Customer (requester) | Fast, accurate help; urgency-appropriate response; trustworthy communication | Long waits, duplicated answers, uncertain outcomes; impact varies by urgency/tier | Honest, cited, disclosed responses or timely escalation; no confident wrong answers; reduced wait/effort | EV-23, EV-24, EV-25, EV-26, EV-29, EV-31 |
| Tier 1 support agent | Resolve or triage quickly with confidence; reduce search/writing effort; avoid rework | High queue pressure, painful KB search, snippet reliance, confidence gaps, fear of wrong auto-answers | Drafts with relevant sources, confidence/risk signals, safe escalation recommendations, fewer repetitive lookups | EV-08, EV-09, EV-10, EV-11, EV-12, EV-13, EV-20, EV-21 |
| Tier 2 support engineer | Receive actionable escalations; focus on genuinely hard/sensitive issues | Escalations missing summary/context/tried steps; avoidable escalations; risk of scaling bad knowledge | Escalation package with intent, retrieved docs/citations, decision rationale, uncertainty/what was tried | EV-14, EV-15, EV-16, EV-17, EV-18, EV-32 |
| Technical writer (KB owner) | Maintain accurate, discoverable KB and improve content quality | KB underused due to search mismatch; private unreviewed snippets; unknown doc effectiveness | Retrieval grounded in curated corpus with citations/doc IDs, visibility into gaps/no-doc intents and usage signals | EV-19, EV-20, EV-21, EV-22, EV-35, EV-36, EV-37, EV-39 |
| Support manager / operations lead | Meet SLA/FCR/cost targets safely; explain decisions; manage compliance and fairness | Overload, breaches, failed scaling tactics, limited breakdown visibility, compliance/fairness concerns | Measurable outcome improvements, auditable decision logs, guardrail/monitoring metrics, controlled automation boundaries | EV-01, EV-02, EV-03, EV-04, EV-05, EV-06, EV-07, EV-29, EV-33 |

## 4. Functional requirements

| REQ ID | Statement | Rationale | EV ref(s) | Acceptance test | Priority |
|---|---|---|---|---|---|
| REQ-F-ING-001 | Ingest tickets from **email, live chat, documentation comments, and community forum** and normalize each into a single internal representation while preserving original text and source channel. | Multi-channel intake is required for consistent downstream processing and traceability (A1). | EV-08, EV-23, EV-27, EV-28 | Submit one ticket per channel; system emits a normalized record containing source channel and original raw text/fields. | Must |
| REQ-F-ING-002 | Ingest shall handle missing fields, unusual characters, and empty bodies without crashing and shall produce a defined fallback/validation outcome. | Robust intake prevents silent drops and supports unattended runs (A1, A11). | EV-05, EV-29 | Feed malformed/empty/unicode inputs; pipeline returns structured error/fallback result and continues processing. | Must |
| REQ-F-CLS-001 | Classify every ticket with an **intent category** and **urgency level**, and attach a numeric confidence reflecting model/system certainty. | Triage and routing depend on intent/urgency and calibrated confidence (A2). | EV-03, EV-09, EV-23, EV-30, EV-31 | For a labeled sample, classifier outputs intent, urgency, and confidence for all tickets (no exceptions). | Must |
| REQ-F-CLS-002 | On classification failure/uncertainty, return a defined fallback (not an exception) and record alternatives considered (not only top choice). | Safe degradation and explainability require visible uncertainty (A2, A8). | EV-05, EV-11, EV-14, EV-16 | Induce classifier failure/low-confidence case; output includes fallback label/state and ranked alternatives with scores/confidences. | Must |
| REQ-F-RET-001 | Retrieve ranked passages from the supplied curated documentation corpus with scores and identifiers that resolve to real corpus articles/chunks. | Grounded answers and verifiable citations require traceable retrieval (A3, A4). | EV-10, EV-19, EV-20, EV-21, EV-24, EV-35, EV-36, EV-39 | Query known questions; results include passage text/snippet, score, and resolvable `doc_id`/chunk identifiers. | Must |
| REQ-F-RET-002 | Apply a relevance threshold and return no passages (rather than irrelevant passages) when evidence is insufficient; support chunking strategy decisions with metadata. | Prevents weak grounding/hallucination and supports no-doc/unclear cases (A3, A4). | EV-22, EV-37, EV-38, EV-39 | Query out-of-scope/no-match inputs; retriever returns empty/insufficient-evidence result and logs threshold decision. | Must |
| REQ-F-RTE-001 | Route each ticket to **auto-answer**, **assist/draft**, or **escalate** using a deterministic, data-informed threshold/policy based on confidence, retrieval evidence, intent/risk, and labels/constraints. | Consistent, explainable decisions balance automation value and safety (A3, A6). | EV-03, EV-05, EV-11, EV-12, EV-18, EV-30, EV-31, EV-32, EV-38 | Same input/config yields same routing decision; tests cover answerable, low-confidence, must-not-auto, and no-doc cases. | Must |
| REQ-F-RTE-002 | Every routing decision records a human-readable reason; escalations include a drafted summary, retrieved sources/citations, intent/urgency/confidence, and what is uncertain/tried (where available). | Reduces tier-2 rework and supports accountability (A3, A8). | EV-14, EV-15, EV-16, EV-32 | Inspect escalation payload/log for required context fields and manager-readable rationale. | Must |
| REQ-F-GEN-001 | Generate responses grounded in retrieved passages with citations attached to claims; state plainly when the answer is unknown or evidence is insufficient. | Trustworthy assistance requires grounded, calibrated outputs (A4). | EV-12, EV-21, EV-24, EV-25, EV-31, EV-34 | For supported queries, response contains citations resolvable to corpus IDs; for insufficient evidence, response abstains/defers per policy. | Must |
| REQ-F-GEN-002 | Separate system/developer instructions from ticket/customer content to resist prompt injection and produce output in a defined, machine-parseable structure. | Prevents instruction hijacking and enables automated validation/evaluation (A4, A11). | EV-05, EV-17, EV-22, EV-25 | Injection-style ticket text does not override policy; outputs conform to schema/format contract and parse successfully. | Must |
| REQ-F-VAL-001 | Run validation/guardrails on **every generated response before release** (including demos), checking at minimum for private data/PII leakage and claims unsupported by retrieved sources. | Safety is non-optional and must be enforceable (A5, A7). | EV-05, EV-07, EV-18, EV-21, EV-25, EV-38 | Crafted PII and unsupported-claim cases trigger checks on all runs; evidence shows checks executed pre-release. | Must |
| REQ-F-VAL-002 | Guardrails must be able to **block** release (not only warn) and must record what was checked, findings, and action taken for every evaluated response. | Blocking controls and audit records are required for governance (A5, A7, A8). | EV-05, EV-16, EV-25, EV-33 | Triggering case is blocked/quarantined/escalated per policy; log includes check types, outcomes, and action. | Must |
| REQ-F-HAR-001 | Provide a single documented unattended evaluation harness command that accepts `--input` and `--output` paths, processes every ticket, and produces either a sent/ready answer or a logged escalation/blocked outcome for each (no silent drops). | Final assessment and operational reliability depend on unattended, complete batch processing (A9). | EV-01, EV-04, EV-29, EV-32 | Run harness on a supplied dataset path; output counts reconcile to input count with per-ticket outcomes and no unlogged drops. | Must |
| REQ-F-HAR-002 | Harness shall generate a metrics report (code-calculated) including volume, business, technical, and governance figures required by spec. | Reproducible measurement is required for acceptance and reporting (A9, A10). | EV-04, EV-28, EV-29, EV-30, EV-33 | After run, report contains processed/answered/escalated/blocked counts, FCR/response-time/escalation metrics, precision/recall/retrieval/latency metrics, and decision-log/guardrail/PII-detection counts. | Must |
| REQ-F-OPS-001 | Handle provider outages/timeouts/rate limiting, no-retrieval hits, and malformed inputs by degrading gracefully and continuing operation (queue/backoff/cache/fallback as appropriate) without crashing the full run. | External dependency and input failures are expected; resilience is required (A11). | EV-01, EV-23, EV-28, EV-29 | Induce each failure mode (including provider unavailable/rate-limited); system records failure and continues processing remaining tickets. | Must |
| REQ-F-TST-001 | Provide a single documented test command that runs automated tests and reports results; tests cover core pipeline behaviors and regressions relevant to acceptance criteria. | Verifiable quality and maintainability (A12). | EV-05, EV-28 | Execute documented test command from clean setup instructions; suite runs and reports pass/fail with exit code. | Must |

## 5. Non-functional requirements

| REQ ID | Statement | Rationale | EV ref(s) | Acceptance test | Priority |
|---|---|---|---|---|---|
| REQ-NF-SEC-001 | The system shall prevent private data/PII and secrets from appearing in outbound responses, logs, prompts persisted unnecessarily, or committed artifacts; `.env` must remain uncommitted. | Privacy/compliance and secret hygiene are mandatory (zero-leak target). | EV-05, EV-07, EV-21, EV-25 | Secret/PII scans and redaction tests pass; repo/config review shows placeholders only in `.env.example`; no raw secrets in logs/artifacts. | Must |
| REQ-NF-REL-001 | The system shall achieve graceful degradation and high availability behavior appropriate to free-tier dependencies (target 99.5%+ effective availability behavior/design intent) through retries/backoff, caching, and fallback paths. | Support operations cannot stop for transient provider issues. | EV-01, EV-23, EV-29 | Failure-injection run demonstrates continued processing and bounded recovery behavior; outages/rate limits logged. | Must |
| REQ-NF-PERF-001 | The system shall measure and report latency (median and p95) and be designed to meet **p95 < 3 seconds** for model-assisted response path where feasible under provider constraints, with transparent reporting when constrained. | Live-chat/customer experience requires low latency; constraints must be visible. | EV-08, EV-23, EV-29 | Harness/report outputs median and p95 latency; performance test results documented against target and constraints. | Should |
| REQ-NF-ACC-001 | Classification and grounding quality shall be measured and improved against targets: **precision ≥85%** (per relevant eval definition), **hallucination ≤5%**, **citation accuracy ≥95%**, and **calibration within 5pp** (confidence vs correctness). | Safe automation depends on measurable correctness and calibration. | EV-05, EV-12, EV-25, EV-29, EV-30, EV-31, EV-38 | Evaluation harness/report computes required metrics on designated datasets; calibration/quality review documented. | Must |
| REQ-NF-FAIR-001 | Outcome/quality metrics shall be segmented (at minimum by language fluency, tier, region where available) with a target of **<5 percentage points gap** between groups for key quality outcomes, and disparities investigated. | Fair, equitable service across customer segments. | EV-07, EV-13, EV-26, EV-33 | Report includes segmented metrics and gap calculations; deviations documented with mitigation plan. | Must |
| REQ-NF-EXPL-001 | All automated decisions shall be explainable to a support manager (human-readable rationale, evidence/citations, confidence/threshold basis) and reproducible given same inputs/config. | Trust, compliance review, and operational debugging require explainability/determinism. | EV-07, EV-15, EV-16, EV-21, EV-25, EV-32 | Sampled decision records can be interpreted without code tracing; deterministic routing tests pass. | Must |
| REQ-NF-MAINT-001 | The solution shall use the prescribed/approved stack patterns where applicable (Python 3.10+, documented setup, OpenRouter-first config), maintain clear module boundaries, and record attribution and design decisions. | Reproducibility, maintainability, and assessment requirements. | EV-19, EV-28, EV-39 | README/setup reproducible from clean state; ADR/attribution/traceability artifacts present and current. | Should |

## 6. Cross-cutting concerns (logging, monitoring, governance)

| REQ ID | Statement | Rationale | EV ref(s) | Acceptance test | Priority |
|---|---|---|---|---|---|
| REQ-X-LOG-001 | Record every decision/event needed for audit in an append-only decision log (input reference, predictions/confidence/alternatives, retrieval sources/citations, routing/action, guardrail checks/outcomes, model/prompt/version metadata, timestamps/latency, errors) per A8 schema intent. | Auditability and reconciliation of outcomes to actions. | EV-05, EV-07, EV-16, EV-21, EV-25, EV-31, EV-32 | For a run, every ticket has a corresponding decision record; spot checks reconcile log entries to harness outcomes/metrics. | Must |
| REQ-X-MON-001 | Capture and expose operational metrics/monitoring signals: throughput, latency distribution, error/fallback rates, provider failures/rate limits, guardrail activations, and escalations/blocks by type. | Detect degradation, cost/rate-limit issues, and safety events during runs. | EV-01, EV-06, EV-29, EV-33 | Metrics report and/or run summary includes required operational/governance counters and latency stats. | Must |
| REQ-X-GOV-001 | Enforce governance policies: no-doc and must-not-auto/sensitive cases handled per policy, curated KB grounding over unreviewed snippets, decision traceability, and fairness/compliance review hooks. | Responsible automation and policy compliance. | EV-07, EV-17, EV-18, EV-22, EV-26, EV-33, EV-37, EV-38 | Policy test cases (feature_request/unclear_request/sensitive intents) follow escalation/assist/block rules; governance report documents guardrails and segment checks. | Must |

## 7. Out of scope (v1)

| Item | Rationale | Revisit trigger |
|---|---|---|
| Fully autonomous resolution for all intents (including `feature_request`, `unclear_request`, security/compliance-sensitive cases) | Evidence and policy require abstention/escalation or human handling for high-risk/no-doc cases. | After validated safety/coverage gains and explicit policy approval. |
| Training/fine-tuning on unreviewed agent snippets or non-curated sources | Risk of scaling incorrect/outdated guidance. | Only with curated, reviewed datasets and governance controls. |
| Paid model capacity or spend-dependent architecture | Project must complete within free/open-source/free-tier constraints. | If free-tier constraints are formally waived (not assumed). |
| UI/productization beyond required interface/demo needs (advanced CRM integrations, omnichannel production deployment) | Focus is on core pipeline, evaluation, governance, and acceptance criteria. | Post-capstone/productization phase. |
| Using validation/hidden assessment tickets for tuning/debugging | Violates evaluation integrity. | Never during build; only designated final evaluation process. |

## 8. Assumptions and risks (if wrong)

| ID | Assumption | If wrong | Mitigation / validation | Evidence / basis |
|---|---|---|---|---|
| ASM-01 | `answerable_from_docs` and `expected_doc_ids` labels in development data are sufficiently reliable proxies for discovery/design. | Prioritization/chunking/routing decisions may be biased. | Cross-check with corpus audit, sampled manual review, and later retrieval evaluation on dev data. | EV-30, EV-36, EV-37 |
| ASM-02 | Curated KB (29 docs) remains the authoritative grounding source for v1. | Answers may be incomplete or outdated for real cases. | Cite sources, surface freshness metadata, escalate on low evidence/no-doc intents. | EV-19, EV-21, EV-22, EV-35 |
| ASM-03 | OpenRouter free-tier access is available for development/testing within rate/cost limits. | Latency/failures/blockers during runs. | Backoff/queue/cache/fallback, provider abstraction, graceful degradation; document constraints. | Assumption (Brief/Spec), EV-01 |
| ASM-04 | Thresholds/calibration chosen from development evidence will transfer reasonably to held-out sets. | Over/under-escalation and quality regressions. | Deterministic policy config, calibration measurement, A10 regression checks, no validation tuning. | EV-05, EV-31, EV-32, EV-33 |
| ASM-05 | Segment labels (language_fluency/tier/region) are usable for fairness analysis even if imperfect. | False confidence or missed disparities. | Report sample sizes, confidence/caveats, and multiple segment cuts. | EV-13, EV-26, EV-33 |

## 9. Success measures

| Category | Measure | Target | Baseline / context | Evidence / basis |
|---|---|---|---:|---|
| Business | First contact resolution (FCR) | ≥ 60% | 43.8% dev baseline (brief ~42%) | EV-04, EV-28, EV-29 |
| Business | Escalation rate | ≤ 30% | 56.2% dev baseline (brief ~58%) | EV-04, EV-28, EV-29, EV-32 |
| Business | Average/target time to first reply (product goal) | < 5 minutes | Brief baseline 8–12 hours (dev history has resolution-time field, not first-reply) | EV-01, EV-23, EV-28, EV-29 |
| Business | Customer satisfaction (CSAT) | ≥ 4.0 / 5 | 2.972 mean dev baseline (brief 3.2) | EV-04, EV-25, EV-28, EV-29 |
| Technical | Classification precision | ≥ 85% | To be established on labeled eval runs | EV-30, EV-31 |
| Technical | Hallucination rate (unsupported/ungrounded responses) | ≤ 5% | To be established; must be minimized by grounding/guardrails | EV-05, EV-12, EV-25, EV-38 |
| Technical | Citation accuracy | ≥ 95% | To be established; citations must resolve to real corpus | EV-21, EV-24, EV-35, EV-36 |
| Technical | Latency (p95) | < 3 seconds | To be measured (provider-dependent) | EV-23, EV-29 |
| Technical | Availability / graceful handling under dependency issues | ≥ 99.5% (target behavior/design) | Provider/rate-limit failures expected on free tier | EV-01, EV-29 |
| Governance | Private data in outbound responses | 0 occurrences | Zero tolerance | EV-05, EV-07, EV-25 |
| Governance | Quality gap across customer groups | < 5 percentage points | Dev segments show mixed disparities; monitor by fluency/tier/region | EV-13, EV-26, EV-33 |
| Governance | Calibration (confidence vs correctness) | Within 5 percentage points | To be measured on eval data | EV-05, EV-11, EV-31, EV-32 |

## 10. Coverage mapping (components, cross-cutting, A1–A12)

| Area | Covered by REQs |
|---|---|
| Ingest component | REQ-F-ING-001, REQ-F-ING-002 |
| Classify component | REQ-F-CLS-001, REQ-F-CLS-002 |
| Retrieve component | REQ-F-RET-001, REQ-F-RET-002 |
| Route component | REQ-F-RTE-001, REQ-F-RTE-002 |
| Generate component | REQ-F-GEN-001, REQ-F-GEN-002 |
| Validate component | REQ-F-VAL-001, REQ-F-VAL-002 |
| Logging (cross-cutting) | REQ-X-LOG-001, REQ-F-RTE-002, REQ-F-VAL-002 |
| Monitoring (cross-cutting) | REQ-X-MON-001, REQ-F-HAR-002, REQ-NF-PERF-001 |
| Governance (cross-cutting) | REQ-X-GOV-001, REQ-NF-SEC-001, REQ-NF-FAIR-001, REQ-NF-EXPL-001 |
| A1–A12 | A1: REQ-F-ING-001/002; A2: REQ-F-CLS-001/002; A3: REQ-F-RET-001/002, REQ-F-RTE-001/002; A4: REQ-F-GEN-001/002, REQ-F-RET-001/002; A5: REQ-F-VAL-001/002; A6: REQ-NF-ACC-001, REQ-F-RTE-001; A7: REQ-F-VAL-001/002; A8: REQ-X-LOG-001; A9: REQ-F-HAR-001/002; A10: REQ-F-HAR-002, REQ-F-TST-001 (regression workflow to be implemented); A11: REQ-F-OPS-001, REQ-NF-REL-001; A12: REQ-F-TST-001 |

## 11. Traceability
- Seed mapping: [traceability.csv](traceability.csv) (EV→REQ)
- Evidence register: [../workbooks/evidence_register_complete.csv](../workbooks/evidence_register_complete.csv)
- Each REQ in this document includes `EV ref(s)` and acceptance tests to support rapid traceability and implementation planning.
