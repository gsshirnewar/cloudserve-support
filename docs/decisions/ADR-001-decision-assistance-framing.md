# ADR-001: Frame system as evidence-grounded decision-and-assistance (not chatbot-only)

- **Status:** Accepted (T10 draft)
- **Date:** 2026-11-22
- **Deciders:** Project delivery (design stage)
- **Related REQs:** REQ-F-RTE-001/002, REQ-F-GEN-001/002, REQ-F-VAL-001/002, REQ-X-GOV-001, REQ-NF-EXPL-001
- **Evidence:** EV-03, EV-05, EV-12, EV-16, EV-18, EV-22, EV-25, EV-29, EV-30, EV-31, EV-37, EV-38

## Context
The brief/spec describes multi-step ticket handling (classify, retrieve, route, generate, validate). Stage 1 findings show 71.4% tickets are answerable-from-docs and 62.2% expected auto-respond, yet outcomes remain weak and sensitive/no-doc cases require escalation/abstention. Stakeholders need safe assistance, explainability, and escalation-with-context rather than unconstrained autonomous chat.

## Decision
Implement a pipeline with explicit outcomes: **auto-answer**, **assist/draft**, and **escalate/abstain/block**. Generation is conditional on retrieval evidence, confidence/policy checks, and pre-release validation. Escalations carry intent, evidence, rationale, and uncertainty.

## Rationale
- Matches observed delivery gap (knowledge exists but not safely delivered).
- Reduces risk of wrong/sensitive responses (must-not-auto, no-doc intents).
- Supports tier-1 efficiency and tier-2 handoff quality (“show working”).

## Consequences
- **Positive:** Clear safety boundaries, testable routing, better auditability and user trust.
- **Negative:** More components/state/policy logic than a single chat endpoint.
- **Mitigations:** Deterministic router, structured schemas, reusable escalation/decision-log artifacts.

## Alternatives considered
- **Chatbot-only auto-responder:** rejected due to unsupported-claim/PII/sensitive-case risks and misalignment with evidence.
- **Assist-only (never auto-answer):** deferred; v1 allows policy-gated auto-answer where evidence/confidence/risk permit, subject to evaluation.