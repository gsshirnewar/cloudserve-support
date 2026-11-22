# ADR-004: Always-on, pre-release, blocking guardrails

- **Status:** Accepted (T10 draft)
- **Date:** 2026-11-22
- **Deciders:** Project delivery (design stage)
- **Related REQs:** REQ-F-VAL-001/002, REQ-X-GOV-001, REQ-NF-SEC-001, REQ-X-LOG-001
- **Evidence:** EV-05, EV-07, EV-12, EV-18, EV-21, EV-22, EV-25, EV-37, EV-38

## Context
Stakeholders require zero tolerance for private-data leakage and no confident wrong answers. Spec requires guardrails to run on every generated response before release and to be able to block (A5/A7). Sensitive/no-doc intents and insufficient evidence must not auto-resolve.

## Decision
Run `validate_node` **before every release** in all execution modes. Checks include (minimum) PII/private-data detection and unsupported-claim/grounding verification, plus policy enforcement. Validators can **block/redact/escalate** (fail-safe on validator errors) and must record checks/findings/actions.

## Rationale
- Converts safety from advisory to enforceable control.
- Supports governance metrics (activations, PII detections, blocks) and auditability.
- Aligns with must-not-auto and no-doc escalation boundaries.

## Consequences
- **Positive:** Reduced leakage/hallucination risk; clear evidence for A5/A7.
- **Negative:** Possible over-blocking and added latency.
- **Mitigations:** Tune thresholds/rules on dev data, log reasons, provide escalation-with-context on block.

## Alternatives considered
- **Warn-only guardrails:** rejected (non-compliant with spec intent).
- **Post-release monitoring only:** rejected for safety-critical outbound responses.