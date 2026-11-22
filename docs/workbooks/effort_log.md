# Effort Log

**Project:** CloudServe intelligent support system (Capstone)  
**Rule:** Update at least every 2nd day (T08 gate: log updated; T40 requires ≥1 entry per 2 days and estimate-vs-actual by stage).

| Date | Task(s) | Stage/Phase | Estimate (h) | Actual (h) | What was done | Notes / blockers |
|---|---|---|---:|---:|---|---|
| 2026-11-22 | T01 | Phase A (setup) | 3.0 | 1.5 | Scaffolded `cloudserve-support` structure, configs (`.env.example`, `.gitignore`, requirements, README, ATTRIBUTION), copied datasets, added `scripts/smoke_test.py`. Verified OpenRouter LLM call succeeds with local `.env`; secret-pattern scan clean. | Full smoke test blocked in-session: `sentence-transformers`/`chromadb` not installed and `pip` restricted; embedding dim 384 + Chroma round-trip pending in clean venv. |
| 2026-11-22 | T02 | Phase A/B (governance seed) | 2.0 | 0.8 | Created `docs/governance/decision_log_schema_draft.md` (A8 mapping) and `docs/governance/never_do.md` (ND-01–ND-08 with enforcement mechanisms/evidence). | None. |
| 2026-11-22 | T03 | Phase B (discovery) | 4.5 | 1.5 | Analyzed all 5 stakeholder transcripts; created `evidence_register.csv` (EV-01–EV-28), `stage1_interviews.md`, `contradictions.md` (C1–C4 with data-test plans). | Validation set not used. |
| 2026-11-22 | T04 | Phase B (discovery) | 3.0 | 1.2 | Built and ran `scripts/eda.py` on 500 development tickets (dev-only guard); generated `eda_outputs/*`, `stage1_ticket_data.md`; recorded T04 findings EV-29–EV-34. | Main `evidence_register.csv` locked by another process; findings saved to `t04_evidence_findings.csv` and later consolidated. |
| 2026-11-22 | T05 | Phase B (discovery) | 3.0 | 1.0 | Audited 29 KB articles; produced intent→doc coverage matrix, gaps, and chunking hypothesis in `corpus_audit.md`; created `stage1_data_constraints.md` and EV-35–EV-39. | Validation set not used. |
| 2026-11-22 | T06 | Phase B (discovery) | 2.5 | 0.8 | Completed Stage 1 sections for agent time, stakeholder success definitions, and data/constraints (privacy, free tier, language fluency, regions) with EV/assumption refs in `stage1_agent_time_success_constraints.md`. | None. |
| 2026-11-22 | T07 | Phase B (discovery) | 2.0 | 0.7 | Wrote problem statement citing ≥3 EVs including answerable-from-docs (EV-30); performed transcript-based recognition check and recorded challenge/revision in `stage1_problem_statement.md`. | Challenge/revision documented from evidence/transcript tensions (no external peer review in-session). |
| 2026-11-22 | T08 | Phase B (gate) | 1.5 | 0.8 | Assembled Stage 1 workbook index (`stage1_workbook.md`), proofread section tables, created consolidated evidence register (`evidence_register_complete.csv`, EV-01–EV-39), and updated effort log. | **Repo commit pending:** workspace is not a git repository in this session; main `evidence_register.csv` remained file-locked. |
| 2026-11-22 | T09 | Phase C (requirements) | 7.0 | 2.0 | Created PRD v1 (`docs/prd/PRD_v1.md`) with document control, problem, user groups, functional/non-functional requirements, cross-cutting logging/monitoring/governance, out-of-scope, assumptions, success measures, and A1–A12/component coverage mapping. Seeded EV→REQ traceability in `docs/prd/traceability.csv`. | Delivered in Markdown (plan allows `.md → docx`); can be converted to `PRD_v1.docx` for submission format if required. |
| 2026-11-22 | T10 | Phase C (design) | 7.0 | 2.5 | Started/completed draft T10 artifacts: `docs/design/HLD.md`, `docs/design/LLD.md`, `docs/design/component_req_map.md`, and ADR-001–ADR-006 in `docs/decisions/` (framing, chunking, deterministic routing, blocking guardrails, provider resilience, decision logging). Included schemas/interfaces, LangGraph state/nodes, A11 failure matrix (incl. provider fully down), and REQ/A-criteria mappings. | Draft design ready for review/refinement in T11+; threshold values and eval calibration to be finalized with eval plan/runs. |

## Summary (to date)
| Stage | Estimated (h) | Actual (h, logged) | Variance note |
|---|---:|---:|---|
| T01–T10 (setup + Stage 1 + PRD + design draft) | 35.5 | 12.8 | Actuals reflect focused in-session documentation/design; implementation, calibration, and validation will add time. |

> Continue logging per task/day; reconcile final estimate-vs-actual by stage for T40 submission package.
