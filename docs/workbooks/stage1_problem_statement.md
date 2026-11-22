# Stage 1 — Problem Statement and Validation (T07)

**Date:** 2026-11-22  
**Evidence sources:** [evidence_register.csv](evidence_register.csv) (EV-01–EV-28), [t04_evidence_findings.csv](t04_evidence_findings.csv) (EV-29–EV-34), [t05_evidence_findings.csv](t05_evidence_findings.csv) (EV-35–EV-39), [stage1_interviews.md](stage1_interviews.md), [eda_outputs/eda_summary.md](eda_outputs/eda_summary.md), [corpus_audit.md](corpus_audit.md)

## 1. Problem statement

CloudServe’s support operation is failing to deliver timely, reliable first-contact help to customers and efficient workflows to support staff because **existing answers in the curated knowledge base are not consistently found, applied, and delivered with confidence at the point of need**. On the development ticket sample (n=500), **71.4% of tickets are labeled `answerable_from_docs` and 62.2% as `expected_auto_respond`** (`EV-30`, `EV-36`), yet baseline outcomes remain weak: **43.8% FCR, 56.2% escalation, 21.6% repeat contact, CSAT mean 2.972** (`EV-29`). Even among doc-answerable tickets, outcomes show a delivery gap (FCR 61.34%, escalation 38.66%, repeat contact 16.25%), and among expected-auto tickets escalation remains 29.58% (`EV-31`), indicating that knowledge availability alone is insufficient without trustworthy retrieval, grounded response drafting, and risk-aware routing.

This problem affects multiple groups in different ways:
- **Customers (e.g. Ravi)** wait too long and bear urgency-dependent impact; many self-search documentation while waiting and often receive the same answer later, so delays and inconsistency erode trust (`EV-23`, `EV-24`, `EV-25`).
- **Tier 1 agents (e.g. Sofia)** face high queue pressure and spend disproportionate time finding/writing answers because KB search is painful and agents rely on personal snippets; they escalate when unsure or when policy requires it (`EV-08`, `EV-09`, `EV-10`, `EV-11`, `EV-13`).
- **Tier 2 engineers (e.g. Daniel)** receive escalations without sufficient context and spend time on cases that may be tier-1 resolvable, while truly sensitive/complex cases still require expert handling (`EV-14`, `EV-15`, `EV-16`, `EV-18`, `EV-32`).
- **Support leadership (Marcus)** cannot meet SLA/cost/quality goals with current scale tactics and needs explainable, safe improvements that reduce response time and escalations without creating wrong-customer answers or extra agent work (`EV-01`, `EV-02`, `EV-04`, `EV-05`, `EV-07`).
- **Knowledge owners (Ines)** maintain a curated 29-article KB that is relevant but underused internally; unreviewed snippet practices and missing coverage for some intents create quality and governance risks (`EV-19`, `EV-20`, `EV-21`, `EV-22`, `EV-35`, `EV-37`).

**Why “chatbot” is the wrong framing:** Framing this as “build a chatbot” over-focuses on generating conversational replies and under-specifies the real system problem: **triage, retrieval, grounding, confidence calibration, policy-aware escalation, and auditable decision-making**. A generic chatbot can produce fluent but unsupported answers, mishandle sensitive/no-doc cases (`feature_request`, `unclear_request`, security/compliance/billing-dispute/data-location scenarios), and add rework or harm (`EV-05`, `EV-12`, `EV-17`, `EV-18`, `EV-22`, `EV-25`, `EV-37`, `EV-38`). The appropriate framing is an **intelligent, evidence-grounded support decision-and-assistance system** that (a) cites and uses curated KB content where supported, (b) drafts/assists or auto-resolves only within defined confidence and policy boundaries, (c) escalates with context and rationale when it should, and (d) logs decisions and guardrail outcomes for accountability (`EV-16`, `EV-21`, `EV-25`, `EV-34`, `EV-39`).

**How success will be measured (problem-oriented):** improvements against current baselines and targets for FCR, escalation/repeat contact, response/handling latency, CSAT, grounded-answer quality (precision/citation accuracy/hallucination control), policy compliance (zero private-data leakage, correct handling of must-not-auto/escalation cases), and explainability/segment fairness, validated on held-out data per project rules (`EV-04`, `EV-29`, `EV-30`, `EV-33`; targets and governance constraints as specified in brief/spec).

## 2. Evidence basis (selected, ≥3 EV items including answerable-from-docs)

| EV ID | Evidence | Why it supports the problem statement |
|---|---|---|
| **EV-30** | 71.4% of dev tickets labeled `answerable_from_docs`, 62.2% `expected_auto_respond` (overall and by channel/intent) | **Answerable-from-docs finding:** substantial share of demand is addressable from existing knowledge, so the core issue is delivery/grounding/routing rather than lack of KB topics alone. |
| EV-29 | Baseline outcomes: FCR 43.8%, escalation 56.2%, repeat contact 21.6%, CSAT mean 2.972 (n=500 dev) | Quantifies the current performance gap experienced by the organization/customers. |
| EV-31 | Among answerable tickets escalation 38.66% and repeat 16.25%; among expected-auto tickets escalation 29.58% | Shows doc availability does not translate into resolved outcomes without better assistance/automation design. |
| EV-10, EV-20, EV-21 | Agents struggle to find/write answers; KB search/title mismatch; reliance on unreviewed snippets | Explains mechanism behind the delivery/findability gap. |
| EV-05, EV-18, EV-22, EV-37, EV-38 | Wrong answers, sensitive/no-doc cases, and restricted intents require abstention/escalation and controls | Constrains solution framing away from unconstrained chatbot behavior. |
| EV-15, EV-16, EV-32 | Escalations lack context; need “show working”; meaningful avoidable-escalation proxy | Supports escalation-with-context and confidence-aware routing as part of the problem/solution space. |

## 3. Recognition check (transcript-based validation)

Because CloudServe is fictional, the statement was checked against stakeholder transcripts (would each interviewee recognize it?) and revised based on a recorded challenge.

| Stakeholder | Would they recognize this problem? | What resonates / what they would emphasize | Evidence |
|---|---|---|---|
| Marcus Adeyemi (Head of Support) | Yes | Overload, SLA/cost pressure, need to lower response time and raise FCR without wrong customer answers or extra agent work; explainability matters | EV-01, EV-03, EV-04, EV-05, EV-07 |
| Sofia Restrepo (Tier 1 Agent) | Yes | Repetitive tickets, painful KB search, time spent finding/writing answers, need for draft+sources and confidence-aware escalation; fear of wrong auto-answers | EV-08, EV-09, EV-10, EV-11, EV-12 |
| Daniel Okonkwo (Tier 2 Engineer) | Yes, with caution | Many escalations lack context and some may be avoidable, but genuinely hard/sensitive cases remain; system must show working and not scale bad knowledge | EV-14, EV-15, EV-16, EV-17, EV-18 |
| Ines Varga (Technical Writer) | Yes | KB exists and is relevant but hard to discover internally; answers should cite curated articles; no-doc/novel/roadmap cases must not be fabricated | EV-19, EV-20, EV-21, EV-22 |
| Ravi Menon (Customer) | Yes | Waiting is the main pain, urgency varies, self-search sometimes works but duplicates follow-up; automated help is acceptable if honest, cited, disclosed, and not confidently wrong | EV-23, EV-24, EV-25, EV-26 |

## 4. Recorded challenge and revision

| Field | Record |
|---|---|
| **Challenge raised** | “This still reads like ‘build a chatbot to answer tickets automatically’ — but the data and interviews show limits: not all doc-answerable/expected-auto tickets resolve cleanly, some intents have no KB support, sensitive cases must not be auto-answered, and escalation/context quality is part of the problem.” (Challenge grounded in transcript tensions and T04/T05 findings: EV-05, EV-12, EV-14, EV-17, EV-18, EV-22, EV-31, EV-32, EV-37, EV-38.) |
| **Who/what prompted it** | Transcript-based recognition check across Sofia/Daniel/Ines/Ravi concerns plus contradiction verdicts C1–C4 (delivery gap, avoidable-escalation proxy, segment caution, KB adequacy vs access). |
| **Revision made** | Reframed the problem from “automated answering” to an **evidence-grounded support decision-and-assistance system** with explicit boundaries: grounded/cited responses where supported, confidence/policy-aware auto-answer vs assist vs escalate, escalation-with-context (“show working”), abstention for no-doc/must-not-auto cases, and auditable guardrails/logging. Added measurement emphasis on safe routing and outcome quality, not just reply generation. |
| **Result** | Final statement distinguishes knowledge availability (`EV-30`) from delivered outcomes (`EV-29`, `EV-31`) and aligns with stakeholder safety/operational needs, making “chatbot” an insufficient framing. |

## 5. Readiness for next steps
- This problem statement is intended to feed **T08 (Stage 1 workbook gate)** and **T09 (PRD v1)** requirements/traceability.
- Open follow-ups: refine segment/fairness hypotheses with additional analysis in later evaluation design; keep all validation/hidden-set usage out of build-time tuning.
