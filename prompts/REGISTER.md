# Prompt Registry (T13)

**Versioning convention:** `<PROMPT_ID>@vMAJOR.MINOR.PATCH` (prompt/spec revision tracked here; runtime/config must log prompt version per A8).  
**Owner:** Capstone developer (solo)  
**Last updated:** 2026-11-22

## Registered prompts

| Prompt ID | Name | Version | Purpose | REQ refs | Spec file | Test cases | Status |
|---|---|---:|---|---|---|---|---|
| P-CLS-001 | Intent & urgency classification | v1.0.0 | Classify intent/urgency with numeric confidence and alternatives; safe fallback on uncertainty/failure | REQ-F-CLS-001, REQ-F-CLS-002, REQ-F-ING-001/002, REQ-F-RTE-001/002, REQ-X-LOG-001, REQ-NF-ACC-001, REQ-NF-EXPL-001 | [P-CLS-001_intent_urgency_classification.md](P-CLS-001_intent_urgency_classification.md) | TC01 nominal, TC02 empty/missing, TC03 injection, TC04 failure fallback | Draft |
| P-GEN-001 | Grounded answer generation | v1.0.0 | Generate grounded, cited, structured answer/draft; abstain/escalate when evidence insufficient; isolate ticket text | REQ-F-GEN-001, REQ-F-GEN-002, REQ-F-RET-001/002, REQ-F-RTE-001/002, REQ-F-VAL-001, REQ-NF-SEC-001, REQ-NF-ACC-001, REQ-NF-EXPL-001, REQ-X-GOV-001, REQ-X-LOG-001 | [P-GEN-001_grounded_answer_generation.md](P-GEN-001_grounded_answer_generation.md) | TC01 grounded, TC02 insufficient evidence, TC03 injection, TC04 no-doc/sensitive | Draft |
| P-ESC-001 | Escalation summary | v1.0.0 | Manager-readable escalation package with reason, attempts, uncertainty, and retrieved sources | REQ-F-RTE-001/002, REQ-F-RET-001/002, REQ-F-GEN-001, REQ-F-VAL-002, REQ-X-LOG-001, REQ-NF-EXPL-001, REQ-X-GOV-001 | [P-ESC-001_escalation_summary.md](P-ESC-001_escalation_summary.md) | TC01 nominal, TC02 no-doc, TC03 guardrail block, TC04 injection | Draft |
| P-VAL-001 | Groundedness / claim-support check | v1.0.0 | LLM-assist validation of claim support/citation validity against retrieved evidence (pre-release blocking support) | REQ-F-VAL-001/002, REQ-F-GEN-001, REQ-F-RET-001/002, REQ-NF-ACC-001, REQ-NF-SEC-001, REQ-X-LOG-001 | [P-VAL-001_groundedness_claim_support_check.md](P-VAL-001_groundedness_claim_support_check.md) | TC01 supported, TC02 unsupported, TC03 invalid citation, TC04 contradicted | Draft |
| P-VAL-002 | Private data / PII check assist | v1.0.0 | LLM-assist detection of PII/secrets/cross-customer data in outbound text to support block/redact decisions | REQ-F-VAL-001/002, REQ-NF-SEC-001, REQ-X-LOG-001, REQ-X-GOV-001 | [P-VAL-002_private_data_check_assist.md](P-VAL-002_private_data_check_assist.md) | TC01 clean, TC02 PII, TC03 cross-customer, TC04 injection | Draft |
| P-EVAL-001 | Evaluation judge (groundedness & citation) | v1.0.0 | Dev/offline judge for groundedness, citation accuracy, hallucination/abstention quality scoring | REQ-F-GEN-001, REQ-F-RET-001/002, REQ-F-VAL-001/002, REQ-NF-ACC-001, REQ-F-HAR-002, REQ-X-LOG-001 | [P-EVAL-001_judge_groundedness_citation.md](P-EVAL-001_judge_groundedness_citation.md) | TC01 supported, TC02 hallucinated, TC03 correct abstention, TC04 injection | Draft |

## Prompt-injection test tickets
- [prompt_injection_test_tickets.json](prompt_injection_test_tickets.json) — cases INJ-001..INJ-004 (all channels/intents represented) for validating instruction isolation and safety behavior across prompts.

## Traceability checks

### Every prompt → REQ
| Prompt | REQ references (all mapped to PRD) |
|---|---|
| P-CLS-001 | REQ-F-CLS-001, REQ-F-CLS-002, REQ-F-ING-001, REQ-F-ING-002, REQ-F-RTE-001, REQ-F-RTE-002, REQ-X-LOG-001, REQ-NF-ACC-001, REQ-NF-EXPL-001 |
| P-GEN-001 | REQ-F-GEN-001, REQ-F-GEN-002, REQ-F-RET-001, REQ-F-RET-002, REQ-F-RTE-001, REQ-F-RTE-002, REQ-F-VAL-001, REQ-NF-SEC-001, REQ-NF-ACC-001, REQ-NF-EXPL-001, REQ-X-GOV-001, REQ-X-LOG-001 |
| P-ESC-001 | REQ-F-RTE-001, REQ-F-RTE-002, REQ-F-RET-001, REQ-F-RET-002, REQ-F-GEN-001, REQ-F-VAL-002, REQ-X-LOG-001, REQ-NF-EXPL-001, REQ-X-GOV-001 |
| P-VAL-001 | REQ-F-VAL-001, REQ-F-VAL-002, REQ-F-GEN-001, REQ-F-RET-001, REQ-F-RET-002, REQ-NF-ACC-001, REQ-NF-SEC-001, REQ-X-LOG-001 |
| P-VAL-002 | REQ-F-VAL-001, REQ-F-VAL-002, REQ-NF-SEC-001, REQ-X-LOG-001, REQ-X-GOV-001 |
| P-EVAL-001 | REQ-F-GEN-001, REQ-F-RET-001, REQ-F-RET-002, REQ-F-VAL-001, REQ-F-VAL-002, REQ-NF-ACC-001, REQ-F-HAR-002, REQ-X-LOG-001 |

**Result:** every registered prompt references one or more PRD requirements.

### Every generation/validation REQ → prompt
| Generation/validation REQ | Covered by prompt(s) | Notes |
|---|---|---|
| REQ-F-GEN-001 (grounded, cited, state unknown) | P-GEN-001, P-VAL-001, P-EVAL-001 | P-GEN-001 produces; P-VAL-001/EVAL-001 verify support/citations/abstention |
| REQ-F-GEN-002 (instruction/data separation, parseable structure) | P-GEN-001 (primary), P-CLS-001/P-ESC-001/P-VAL-001/P-VAL-002/P-EVAL-001 | All prompts enforce untrusted delimited ticket/data blocks and JSON schemas |
| REQ-F-VAL-001 (pre-release checks incl. PII and unsupported claims) | P-VAL-001, P-VAL-002, P-EVAL-001 (dev evaluation), P-GEN-001 (compliance) | Runtime validation combines deterministic checks + P-VAL-001/002 assists; P-EVAL-001 supports measurement |
| REQ-F-VAL-002 (blocking + recorded findings/actions) | P-VAL-001, P-VAL-002, P-ESC-001 | P-VAL-001/002 emit block/escalate recommendations and findings; escalation captures outcomes/context |

**Result:** all generation and validation PRD requirements are mapped to one or more prompt specs (with implementation/runtime components responsible for enforcement/logging per design).

## Change control
- Bump version on any instruction/schema/rubric change; update spec file, REGISTER row, and decision log/PR references as applicable.
- Keep customer/ticket content isolated in delimited data blocks in all templates and runtime integrations.