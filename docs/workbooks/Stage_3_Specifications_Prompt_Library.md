# Stage 3 — Specifications & Prompt Library (T13)

**Date:** 2026-11-22  
**Owner:** Capstone developer (solo)  
**Depends on:** T09 (PRD), T10 (design), T12 (sprint plan)

## 1. Deliverables
- Prompt specs (versioned): [`prompts/P-CLS-001_intent_urgency_classification.md`](../../prompts/P-CLS-001_intent_urgency_classification.md), [`prompts/P-GEN-001_grounded_answer_generation.md`](../../prompts/P-GEN-001_grounded_answer_generation.md), [`prompts/P-ESC-001_escalation_summary.md`](../../prompts/P-ESC-001_escalation_summary.md), [`prompts/P-VAL-001_groundedness_claim_support_check.md`](../../prompts/P-VAL-001_groundedness_claim_support_check.md), [`prompts/P-VAL-002_private_data_check_assist.md`](../../prompts/P-VAL-002_private_data_check_assist.md), [`prompts/P-EVAL-001_judge_groundedness_citation.md`](../../prompts/P-EVAL-001_judge_groundedness_citation.md)
- Registry/traceability: [`prompts/REGISTER.md`](../../prompts/REGISTER.md)
- Prompt-injection test tickets: [`prompts/prompt_injection_test_tickets.json`](../../prompts/prompt_injection_test_tickets.json) (INJ-001–INJ-004)

## 2. Prompt coverage (required T13 set)

| # | Required prompt | Prompt ID / Version | REQ refs (primary) | Notes |
|---|---|---|---|---|
| 1 | Intent/urgency classification with confidence + alternatives | P-CLS-001 @ v1.0.0 | REQ-F-CLS-001/002 | Includes fallback, uncertainty flags, alternatives, JSON schema |
| 2 | Answer generation (grounded, cited, "I don't know", structured JSON, ticket isolated) | P-GEN-001 @ v1.0.0 | REQ-F-GEN-001/002, REQ-F-RET-001/002 | Ticket/evidence in delimited untrusted blocks; abstain/escalate on insufficient evidence |
| 3 | Escalation summary | P-ESC-001 @ v1.0.0 | REQ-F-RTE-001/002 | Manager-readable reason, tried/uncertain, sources, policy flags |
| 4 | Groundedness/claim-support check | P-VAL-001 @ v1.0.0 | REQ-F-VAL-001/002, REQ-F-GEN-001 | LLM-assist for support/citation validity; conservative block/escalate guidance |
| 5 | Private-data check assist (LLM-based) | P-VAL-002 @ v1.0.0 | REQ-F-VAL-001/002, REQ-NF-SEC-001 | LLM-assist complement to deterministic PII/secret rules; masked findings |
| 6 | Eval judge prompts | P-EVAL-001 @ v1.0.0 | REQ-NF-ACC-001, REQ-F-HAR-002, REQ-F-GEN-001 | Dev/offline groundedness + citation + abstention scoring |

## 3. Acceptance criteria checklist (T13)

| Criterion | Evidence | Status |
|---|---|---|
| Each prompt has ID, version, owner, purpose, input/output schema, REQ ref, known failure modes, ≥3 test cases | All six prompt spec files + REGISTER | Complete |
| Prompt traceability check complete (every prompt → REQ) | [prompts/REGISTER.md](../../prompts/REGISTER.md) “Every prompt → REQ” table | Complete |
| Every generation/validation REQ → prompt | [prompts/REGISTER.md](../../prompts/REGISTER.md) “Every generation/validation REQ → prompt” table (GEN-001/002, VAL-001/002 mapped) | Complete |
| Customer text never interpolated into the instruction part | All specs require ticket/customer content only inside `<ticket_input>` (and evidence in separate data blocks) marked untrusted; templates/instructions prohibit following embedded commands | Complete (spec-level control; to be enforced in implementation) |
| Prompt-injection test tickets included | [prompts/prompt_injection_test_tickets.json](../../prompts/prompt_injection_test_tickets.json) (INJ-001–INJ-004) referenced by REGISTER and prompt TCs | Complete |

## 4. Component/spec alignment notes
- **Classification:** P-CLS-001 outputs align with `Classification`/routing inputs in LLD (intent, urgency, confidence, alternatives, fallback).
- **Generation:** P-GEN-001 structured claims/citations/abstention align with `Answer` schema and pre-release validation (P-VAL-001/002).
- **Escalation:** P-ESC-001 supports REQ-F-RTE-002 escalation package (summary, sources, uncertainty, reason).
- **Validation:** P-VAL-001/002 are assistive prompts; release blocking remains enforced by deterministic validators and pipeline policy (A5/A7).
- **Evaluation:** P-EVAL-001 used in dev evaluation/harness workflows per eval plan (not a runtime release gate).

## 5. Risks / follow-ups
- Final intent/urgency label taxonomies and policy enums must be pinned in config before implementation tests.
- Runtime must log `prompt_id@version` in decision records (A8).
- Deterministic PII/secret rules and citation-ID resolvers must be implemented alongside LLM-assist prompts; conservative fallback on prompt/parse failures.
- Judge prompt/rubric may be iterated in dev only (version bumps recorded); validation-set usage remains one-time per protocol.