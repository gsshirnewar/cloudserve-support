# Stage 4 — Sprint Plan & Milestones (T12)

**Version:** 0.1 (draft)  
**Date:** 2026-11-22  
**Scope:** CloudServe capstone implementation, evaluation, hardening, and submission (W2–W3)  
**Inputs:** [PRD_v1.md](../prd/PRD_v1.md), [HLD.md](../design/HLD.md), [LLD.md](../design/LLD.md), [eval_plan.md](../design/eval_plan.md), [test_plan.md](../design/test_plan.md), [project_plan_task.md](../../../01_Read_First/project_plan_task.md)

## 1. Capacity and assumptions

| Week | Available capacity (realistic) | Notes |
|---|---:|---|
| W2 (build + harness + rehearsal) | 32 h | Focused build week; accounts for context switching, debugging, provider latency/rate limits, and documentation |
| W3 (calibration, eval, hardening, packaging) | 28 h | Includes regression/final validation protocol execution, report/doc polish, demo packaging |
| **Total planned capacity** | **60 h** | Excludes prior discovery/design effort already logged (T01–T11) |

**Team/ownership:** Solo execution — **Owner (all items): Capstone developer (solo)**.  
**Buffer policy:** ≥15% reserve within each week/day plan for defects, environment issues, and repro runs (see §5).  
**Constraints:** dev-only tuning; validation set used once at end (logged); OpenRouter-first with resilience/cache; no secret commits.

## 2. Backlog (tasks → sprint items)

> **Definition of Done (DoD) is written before work starts** for every item below. Status reflects plan baseline at T12.

| ID | Plan task(s) | Backlog item | Est (h) | Depends on | Owner | DoD (before work) | Status |
|---|---|---|---:|---|---|---|---|
| B00 | T01–T11 | Discovery, PRD, design, eval/test planning | 39.5 (plan) | — | Capstone developer (solo) | Artifacts exist in repo/workspace, traceable (EV/REQ/ADR/tests), and reviewed for next-phase readiness | Done (draft/partial verification noted) |
| B01 | T13 | Specifications & prompt library (Stage 3) | 6 | T09,T10,T12 | Capstone developer (solo) | Versioned prompts/specs created (`prompts/*`, `prompts/REGISTER.md`), each with ID/version/owner/purpose/I-O schema/REQ ref/failure modes/≥3 test cases; traceability complete; ticket text isolated from instructions; injection test cases included | Planned |
| B02 | T14 | Skeleton, config, schemas, logging, CI stub | 3 | T10 | Capstone developer (solo) | `config.py` (env-driven), Pydantic schemas, structured logging, `pytest` runs with ≥1 trivial test, `python -m evaluation.harness --help` shows `--input/--output`, optional lint/type checks pass or documented | Planned |
| B03 | T15 | LLM provider layer with resilience | 5 | T14 | Capstone developer (solo) | Provider abstraction + disk cache + retry/backoff+jitter + timeout + rate limiter + structured-output retry + typed offline/degraded mode + outage simulation; cache-hit and failure tests pass per A11/T15 criteria | Planned |
| B04 | T16 | Ingest (Checkpoint D1) | 4 | T14 | Capstone developer (solo) | All 4 channels normalize to one shape preserving raw/channel; edge cases handled; flagged/logged rejections instead of batch-stopping exceptions; 500 dev tickets ingest with 0 failures | Planned |
| B05 | T17 | Decision log (persistent store) | 4 | T14,T02 | Capstone developer (solo) | SQLite schema + API writes one record per ticket in `finally`; required A8 fields populated; reconcile shows processed==logged; survives restart; 20-ticket sample incl. failures yields 20 rows | Planned |
| B06 | T18 | Retrieval layer (Checkpoint D2) | 6 | T05,T14 | Capstone developer (solo) | Idempotent Chroma index build, stable chunk IDs resolving to corpus, ranked scored results, relevance threshold returns empty on off-topic/no-hit, baseline hit-rate recorded in ADR/notes, rebuild command works | Planned |
| B07 | T19 | Classification with calibrated confidence (Checkpoint D3) | 7 | T15,T13,T04 | Capstone developer (solo) | Intent+urgency+confidence+alternatives returned; fallback on failure/outage without exception; dev-holdout precision and calibration (ECE) measured and recorded | Planned |
| B08 | T20 | Router (Checkpoint D3) | 4 | T18,T19,T17 | Capstone developer (solo) | Deterministic pure routing with config thresholds/policy rules; manager-readable reasons; escalation package includes summary+sources+uncertainty; same input => identical decision; Brief decision-tree branches tested | Planned |
| B09 | T21 | Generation (Checkpoint D4) | 6 | T18,T13,T15 | Capstone developer (solo) | Grounded structured answers with citations validated against retrieved chunks; abstain/escalate on insufficient evidence; prompt-injection isolation; parseable output with retry/fallback | Planned |
| B10 | T22 | Validation & guardrails (Checkpoint D4) | 6 | T21 | Capstone developer (solo) | Always-on validator (PII, unsupported claims, tone/policy) before release; blocking escalations logged with fired checks; no harness bypass; engineered PII/unsupported fixtures blocked with evidence | Planned |
| B11 | T23 | Pipeline orchestration + FastAPI | 5 | T16–T22 | Capstone developer (solo) | LangGraph pipeline with degraded node handling, required API endpoints, one ticket/channel demo, chaos/dependency failure continues batch, each ticket reaches terminal state `answered|escalated|blocked` | Planned |
| B12 | T24 | Evaluation harness & metrics report | 6 | T23 | Capstone developer (solo) | CLI runs unattended on arbitrary schema-matching input, no silent drops, checkpoint/resume-safe if implemented or documented, code-calculated Spec §04+ metrics, reconciliation asserted, exit 0 with per-ticket failure accounting | Planned |
| B13 | T25 | Gate rehearsal: unattended full run (W2D5) | 4 (+run) | T24 | Capstone developer (solo) | Full unattended dev run completes end-to-end, metrics/decision logs/reconciliation artifacts produced, failures analyzed and tracked, runbook/commands recorded for repeatability | Planned (milestone) |
| B14 | T26 | Threshold tuning & calibration on dev | 5 | T25,T19,T20 | Capstone developer (solo) | Sweep/calibration executed per eval plan, operating thresholds selected and documented (ADR/config), ECE/reliability and tradeoffs recorded, deterministic routing preserved | Planned |
| B15 | T27 | Error analysis & remediation | 5 | T25,T26 | Capstone developer (solo) | Failure taxonomy + sampled review completed, prioritized fixes implemented, regression tests added/updated, measurable improvement or justified tradeoff documented | Planned |
| B16 | T28 | Regression, fairness, and governance checks | 4 | T27 | Capstone developer (solo) | A10-style regression comparison, fairness slices/gaps computed, governance/PII/guardrail evidence compiled, zero released PII on tested fixtures/runs | Planned |
| B17 | T29 | Final validation run (one-time) + reporting | 4 (+run) | T28,T11 | Capstone developer (solo) | Freeze manifest created; **single** validation run executed and logged (date, run count=1), final metrics/report generated without post-hoc tuning | Planned (gated) |
| B18 | T30–T32 | Docs, demo, packaging/submission | 6 | T29 | Capstone developer (solo) | README/runbook updated, demo script/assets prepared, submission bundle/docs complete per spec, secrets excluded, reproducibility instructions verified | Planned |
| B19 | Buffer / defect triage | Unplanned fixes, reruns, env issues | 9 | ongoing | Capstone developer (solo) | Critical defects triaged with owner/actions, buffer usage logged, sprint commitments adjusted via drop-list if needed without breaking gated milestones | Reserved (≥15%) |

**Estimated implementation+closure work (B01–B18):** 84 h planned effort against 60 h capacity → managed by prioritization, scope control, and **explicit drop list** (W3D5/W3D6 per plan). **Reserved buffer B19:** 9 h (~15% of 60 h capacity).

## 3. Day-by-day plan (W2–W3)

### Week 2 — Build, harness, rehearsal (target 32 h + buffer within day)

| Day | Planned items | Primary outcomes / checkpoints | Exit criteria for day |
|---|---|---|---|
| W2D1 | B01 (start/complete specs-prompts core), B02 skeleton/config/schemas, B04 ingest start | Prompt/spec baseline; runnable skeleton/tests/help; ingest normalization started (**D1 prep**) | `pytest` runs, harness `--help` works, initial normalized tickets printed |
| W2D2 | B04 complete, B05 decision log, B03 provider resilience start | **Checkpoint D1** ingest complete; persistent decision logging; provider abstraction/cache/backoff scaffold | 4-channel shape parity, decision log write/reconcile prototype, no batch crash on malformed inputs |
| W2D3 | B03 complete, B06 retrieval/chunking/index, B18 doc notes | **Checkpoint D2** retrieval baseline; resilient provider with simulation modes | Cache hit verified, off-topic returns empty, chunk IDs resolvable, index rebuild command |
| W2D4 | B07 classification+calibration hooks, B08 router, B09 generation start | **Checkpoint D3** classify/route integrated; grounded generation path started | Deterministic routing tests pass, fallback on classifier failure, escalation reasons logged |
| W2D5 | B09 complete, B10 validation/guardrails, B11 orchestration/API, B12 harness (critical path), **B13 gate rehearsal** | **Checkpoint D4/D5:** generate+validate wired, pipeline/API runnable, harness unattended full dev run attempted/completed | **Unattended full run included (milestone):** end-to-end dev run executed, `processed==logged`, metrics report produced, failures triaged into W3 backlog |

### Week 3 — Tune, evaluate, harden, submit (target 28 h + buffer)

| Day | Planned items | Primary outcomes | Exit criteria for day |
|---|---|---|---|
| W3D1 | B14 threshold tuning & calibration | Operating thresholds selected from dev sweeps/CV | Config/ADR updated, ECE/reliability and tradeoff artifacts saved |
| W3D2 | B15 error analysis & remediation (priority fixes) | Top failure modes addressed with tests | Regression tests added; key metrics/errors improved or justified |
| W3D3 | B16 regression, fairness, governance checks | Evidence bundle for A7–A10/governance | Regression comparison, fairness slices/gaps, guardrail/PII evidence recorded |
| W3D4 | B17 freeze + **final validation run (one-time)** + report drafting | Validation metrics captured per protocol | Manifest frozen, validation run count/date logged, report generated from code outputs |
| W3D5 | B18 docs/demo/packaging; apply drop-list if needed | Submission-ready docs/demo bundle | README/runbook/demo steps reproducible; excluded secrets/forbidden data confirmed |
| W3D6 (contingency/drop day) | Buffer, critical fixes only, final packaging checks | Risk burn-down / submission completion | All must-have acceptance criteria met or explicitly deferred per drop list |

## 4. Explicit drop list (agreed priority-based de-scope)

If schedule or stability risk threatens gated milestones (especially **W2D5 unattended full run** and **W3D4 one-time validation**), drop/defer in this order:

| Priority | Drop/defer item | Keep instead (must-have) | Trigger |
|---:|---|---|---|
| D1 | UI polish / Streamlit extras beyond minimal demo needs | CLI/API + harness + reproducible evidence | >4h slip by W2D4 or unstable pipeline |
| D2 | Advanced retrieval variants (hybrid/reranker experiments) beyond baseline Chroma+threshold | Correct, traceable retrieval with measured hit rate and citations | Retrieval quality work blocks D4/D5 integration |
| D3 | Additional provider/model experiments beyond OpenRouter-first configured path | Resilient OpenRouter path + cache + degraded mode + documented config | Rate limits/cost/time instability |
| D4 | Non-critical optimization (latency micro-tuning, extra dashboards) | Correctness, guardrails, logging, required metrics report | W3D2+ defects consume buffer |
| D5 | Extended narrative/visual documentation polish | Complete, accurate required docs (PRD/design/eval/test/runbook/ADR evidence) | Submission deadline pressure |

**Never drop:** unattended harness run capability, decision logging/A8 evidence, blocking guardrails/PII safety checks, reproducible metrics calculation, validation-once protocol compliance, or required A1–A12 test evidence.

## 5. Buffer and risk controls (≥15%)
- **Reserved buffer:** 9 h total (B19), distributed as ~1–1.5 h/day slack plus W3D6 contingency.
- **Burn-down rule:** log buffer usage in daily check-in; when cumulative slip > buffer, invoke drop list top-down and escalate scope decision.
- **Risk controls:** cache LLM/embedding calls, mocked providers for tests, checkpoint/resume-safe harness runs where possible, feature flags only for tightening safety (not disabling guardrails), daily reconciliation checks (`processed == logged`).

## 6. Daily check-in record

| Date | Day | Plan focus | Done | Blockers/risks | Buffer used (h) | Next actions | Drop-list invoked? |
|---|---|---|---|---|---:|---|---|
| 2026-11-22 | T12 planning | Sprint plan authored | B00 baseline confirmed; T12 plan created | None recorded | 0.0 | Start B01/B02 (T13/T14) per W2D1 | No |
| YYYY-MM-DD | W2D1 |  |  |  |  |  |  |
| YYYY-MM-DD | W2D2 |  |  |  |  |  |  |
| YYYY-MM-DD | W2D3 |  |  |  |  |  |  |
| YYYY-MM-DD | W2D4 |  |  |  |  |  |  |
| YYYY-MM-DD | W2D5 | **Gate rehearsal (unattended full run)** |  |  |  |  |  |
| YYYY-MM-DD | W3D1 |  |  |  |  |  |  |
| YYYY-MM-DD | W3D2 |  |  |  |  |  |  |
| YYYY-MM-DD | W3D3 |  |  |  |  |  |  |
| YYYY-MM-DD | W3D4 | **Final validation run (one-time)** |  |  |  |  |  |
| YYYY-MM-DD | W3D5 |  |  |  |  |  |  |
| YYYY-MM-DD | W3D6 | Contingency/submission |  |  |  |  |  |

## 7. Milestone acceptance gates
- **W2D5 (Gate rehearsal, T25):** unattended full dev run completes; metrics and decision-log reconciliation artifacts produced; no silent drops.
- **W3D4 (Final validation, T29):** frozen config/prompts/thresholds; single validation run executed; date and run count recorded in manifest/report.
- **Submission readiness:** A1–A12 evidence/tests mapped, required docs packaged, reproducible commands documented, secrets and forbidden datasets excluded.