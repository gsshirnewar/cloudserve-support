# ADR-003: Deterministic, pure-function routing policy

- **Status:** Accepted (T10 draft)
- **Date:** 2026-11-22
- **Deciders:** Project delivery (design stage)
- **Related REQs:** REQ-F-RTE-001/002, REQ-NF-ACC-001, REQ-NF-EXPL-001, REQ-X-LOG-001
- **Evidence:** EV-05, EV-11, EV-14, EV-16, EV-18, EV-30, EV-31, EV-32, EV-37, EV-38

## Context
Routing must balance automation value and safety using classification confidence, retrieval evidence, and policy constraints (must-not-auto/no-doc/sensitive). A11/A6 require reproducible behavior and explainable decisions.

## Decision
Implement router as a **pure function**:
`route(classification, retrieval, thresholds, policy_flags, ticket_context) -> RouteDecision` producing `auto_answer|assist_draft|escalate|block`, reason code/text, and thresholds/policy flags used. No I/O, randomness, or hidden state.

## Rationale
- Same inputs/config yield same decision (testable and auditable).
- Manager-readable reasons and escalation packaging address tier-2 context gaps.
- Thresholds/policy can be calibrated from development data without changing determinism.

## Consequences
- **Positive:** Reproducibility, simpler unit tests, clear governance.
- **Negative:** Complex cases require careful policy/threshold design; model uncertainty still upstream.
- **Mitigations:** Record alternatives/confidence upstream, log all routing inputs/outputs, iterate thresholds via eval plan.

## Alternatives considered
- **LLM-decided routing:** more flexible but less deterministic/explainable and harder to audit.
- **Static intent-only rules:** insufficient for evidence/confidence/risk-aware decisions.