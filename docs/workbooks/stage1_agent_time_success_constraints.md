# Stage 1 — Agent Time, Success Definitions, and Constraints (T06)

**Date:** 2026-11-22  
**Depends on:** T03–T05 (interviews, ticket profiling, corpus audit)  
**Evidence sources:** [evidence_register.csv](evidence_register.csv) (EV-01–EV-28), [t04_evidence_findings.csv](t04_evidence_findings.csv) (EV-29–EV-34), [t05_evidence_findings.csv](t05_evidence_findings.csv) (EV-35–EV-39), [stage1_ticket_data.md](stage1_ticket_data.md), [corpus_audit.md](corpus_audit.md), [stage1_data_constraints.md](stage1_data_constraints.md)

> Acceptance note: every table row includes an `EV-` reference or is explicitly labelled `Assumption`.

## 1. Where agent time goes

| Role / actor | Activity / time sink | Impact on workflow and outcomes | Evidence / basis |
|---|---|---|---|
| Tier 1 support agent (Sofia) | Queue triage and breach-avoidance sorting (oldest first) under high volume (40–70 tickets/day; Mondays worst) | Time spent prioritizing by age/SLA risk rather than issue complexity/value; reactive handling under pressure | EV-08 |
| Tier 1 support agent (Sofia) | Handling repetitive/familiar tickets (password lockouts, rate limits, invoice questions, deployment rollbacks) | ~7/10 tickets felt familiar, but responses still require lookup/writing and outcomes vary; opportunity for fast grounded assistance | EV-09, EV-30, EV-31 |
| Tier 1 support agent (Sofia) | Finding and writing answers (poor KB search/findability; reliance on personal snippet files) | Major effort sink; slows first response and increases inconsistency/risk of unreviewed guidance | EV-10, EV-20, EV-21, EV-24, EV-36 |
| Tier 1 support agent (Sofia) | Escalation decisions and handoffs (unknown/confidence gaps, mandatory security cases) | Time spent judging confidence/policy; avoidable and required escalations both consume capacity | EV-11, EV-18, EV-32, EV-38 |
| Tier 1 support agent (Sofia) | Serving non-fluent English customers (longer clarification/communication cycles) | Additional handling time and potential quality/CSAT risk; requires careful segment-aware design | EV-13, EV-33 |
| Tier 2 support engineer (Daniel) | Reworking escalations lacking summary/context/tried steps | Time wasted reconstructing history instead of solving the underlying issue | EV-15, EV-16 |
| Tier 2 support engineer (Daniel) | Handling escalations that may be tier-1 resolvable with confidence/findability vs genuinely complex cases | Capacity consumed by potentially avoidable escalations (~half by experience; proxy evidence suggests meaningful avoidable share) | EV-14, EV-32 |
| Tier 2 support engineer (Daniel) | Validating/correcting risky or outdated knowledge propagated informally | Extra effort to prevent scaling mistakes from unreviewed snippets/practices | EV-17, EV-21 |
| Technical writer (Ines) | Maintaining curated KB (29 articles) while internal discovery remains poor | Documentation exists but is underused operationally due to title/exact-term search mismatch; limits leverage of existing knowledge | EV-19, EV-20, EV-35, EV-36 |
| Support leadership (Marcus) | Managing overload, SLA breaches, and ineffective scaling interventions (hiring, canned responses, outsourcing) | Leadership time/attention focused on throughput and cost pressures without clear evidence-backed breakdown | EV-01, EV-02, EV-04, EV-06, EV-29 |
| Customer (Ravi) / requester-side time | Waiting for responses and self-searching docs (sometimes duplicated later) | Delay cost varies by urgency; self-service succeeds only part of the time, creating avoidable frustration and repeat effort | EV-23, EV-24, EV-31 |

## 2. What each stakeholder counts as success

| Stakeholder | Role / perspective | Success definition (what “good” looks like) | Evidence / basis |
|---|---|---|---|
| Marcus Adeyemi | Head of Customer Support | Lower response time and improved first-contact resolution without adding headcount; “easy” tickets resolved safely so humans focus on hard cases; avoid wrong customer-facing answers and avoid creating extra agent work; maintain explainability for compliance and respect enterprise SLA sensitivity | EV-03, EV-04, EV-05, EV-07 |
| Sofia Restrepo | Tier 1 Support Agent | Reduced time spent finding/writing answers via useful drafts and attached relevant KB pages/sources; higher confidence and fewer unnecessary escalations where safe; no wrong auto-answers that create angry follow-ups; better handling/support for harder-to-serve cases (e.g. non-fluent English) | EV-10, EV-11, EV-12, EV-13, EV-33 |
| Daniel Okonkwo | Tier 2 Support Engineer | Fewer avoidable escalations; escalations arrive with context (intent, relevant docs, what was tried, what is uncertain) so effort goes to genuinely hard issues; system shows its working and does not scale outdated/wrong knowledge; sensitive categories handled by policy | EV-14, EV-15, EV-16, EV-17, EV-18, EV-32 |
| Ines Varga | Technical Writer (KB owner) | KB content is discoverable and used (retrieval grounded in curated articles, not private snippets); answers cite source articles for diagnosis/improvement; system avoids unsupported answers for topics docs do not cover (feature requests, roadmap/timing, novel incidents) | EV-19, EV-20, EV-21, EV-22, EV-35, EV-36, EV-37 |
| Ravi Menon | Customer (platform lead, business plan) | Fast, useful responses especially for urgent/high-impact issues; honest, cited, and clearly disclosed automated assistance; no confident wrong answers; consistent quality without widening perceived service gaps across plans/tiers | EV-23, EV-24, EV-25, EV-26, EV-33 |

## 3. Data exists and constraints

| Category | Item | What exists / constraint detail | Evidence / basis |
|---|---|---|---|
| Data asset | Development tickets | 500 labeled tickets with channel, content, timestamps, customer/tier/region/language_fluency, intent/urgency/routing/answerability/doc IDs/must-not-auto labels, and outcome history; used for discovery, EDA, and build-time evaluation inputs | EV-27, EV-29, EV-30, stage1_data_constraints.md |
| Data asset | Curated knowledge base | 29 support articles with metadata and content; all referenced by dev expected doc IDs with no missing/unreferenced corpus docs; no-doc intents exist by design | EV-19, EV-35, EV-36, EV-37 |
| Data asset | Validation / assessment data boundaries | 80 validation tickets and hidden assessment set exist conceptually; validation/hidden sets must not be opened or tuned on during build/discovery; harness must accept input path for assessment | EV-27, EV-28, Assumption (Brief §06, Spec test procedure) |
| Data asset | Stakeholder evidence | 5 interviews analyzed with claims/quotes and contradictions tracked; quantitative checks performed on development data only | EV-01–EV-26, EV-28, EV-31–EV-34 |
| Constraint | Privacy / PII / sensitive data | Zero private-data leakage in outbound responses is required; guardrails must detect/block PII/unsupported claims; sensitive cases (e.g. security/compromise, billing disputes, data location/compliance) require strict handling and often escalation/human review | EV-05, EV-07, EV-18, EV-21, EV-22, EV-25, Assumption (Brief §07 governance targets, Spec A5/A7/A11) |
| Constraint | Compliance / explainability / auditability | Decisions must be explainable and logged (inputs, predictions/confidence, sources/citations, action, reason, guardrail outcomes) to support review and governance | EV-07, EV-16, EV-21, EV-25, Assumption (Brief §07/Spec A8, decision_log schema draft) |
| Constraint | Free tier / cost / rate limits | Project must run within free/open-source and provider free-tier allowances (OpenRouter/Groq options); throttling/rate limits/timeouts/outages are expected design conditions requiring backoff/queuing/caching/fallback and graceful degradation (not paid capacity) | EV-01 (cost pressure context), Assumption (Brief §08, Spec §02/§07/A11; OpenRouter-first scaffold in project `.env.example`) |
| Constraint | Language fluency | Tickets/customers include non-fluent English segments; dev evidence shows mixed segment differences (not supporting a single directional claim) so responses/evaluation must be clear, calibrated, and segment-aware | EV-13, EV-26, EV-33, stage1_data_constraints.md |
| Constraint | Regions / tiers / segmentation | Customer tiers and regions affect SLAs/expectations and outcomes; dev data shows segment disparities (e.g. enterprise escalation, regional FCR variation) and customers notice service gaps — fairness/quality monitoring across groups required | EV-07, EV-23, EV-26, EV-33, Assumption (Brief §07 fairness target <5pp gap) |
| Constraint | Grounding and automation boundaries | Answers must be grounded in curated KB with citations; no-doc intents (`feature_request`, `unclear_request`) and must-not-auto-respond/safety cases must escalate/abstain or assist-only; do not scale unreviewed snippet knowledge | EV-12, EV-17, EV-18, EV-21, EV-22, EV-25, EV-31, EV-34, EV-37, EV-38 |
| Constraint | Performance / reliability | Low-latency, reliable behavior needed under provider variability; failures (no retrieval hit, provider timeout/outage, rate limiting, malformed input) must degrade gracefully without crashing; cache/reproducibility encouraged for development | EV-01, EV-23, EV-29, Assumption (Brief §07 latency/availability targets, Spec A11/A12) |

## 4. Traceability notes
- T04/T05 evidence IDs (`EV-29`–`EV-39`) are recorded in `t04_evidence_findings.csv` and `t05_evidence_findings.csv` pending merge into the main `evidence_register.csv`.
- Assumptions are labeled explicitly where project brief/spec or implementation constraints are required but not represented as interview/data evidence rows.
- This artifact, together with `stage1_interviews.md`, `stage1_ticket_data.md`, `corpus_audit.md`, and `stage1_data_constraints.md`, completes the T06 Stage 1 sections with evidence/assumption coverage.