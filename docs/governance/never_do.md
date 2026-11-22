# System "Never Do" Policy and Enforcement Mechanisms (T02)

**Status:** Draft (seed). Each prohibited behavior must be enforced by design/code/configuration, not by trust in the model alone.  
**Traces to:** Build Spec A6–A8, A11; Project Brief §07 (governance conditions), §08 (risk/governance obligations), plan task T02.

## Governing principle
> "If the answer is that the model is generally quite reliable, you have described a hope rather than a control." (Project Brief §08)

Every item below includes a **named enforcement mechanism** (and where it lives/will live) plus logging/evidence expectations.

## Prohibited behaviors and controls

| # | The system must never… | Why (risk) | Primary enforcement mechanism(s) | Where enforced (planned) | Evidence / logging |
|---|---|---|---|---|---|
| ND-01 | **Leak private/sensitive data in outbound responses** (PII, secrets, credentials, tokens, internal-only identifiers not permitted for customer view). | Customer harm, compliance/privacy breach; governance requires zero occurrences. | **Pre-release PII/secret detection and redaction-or-block guardrail** (pattern + heuristic checks; configurable deny rules). If detected in generated output, **block or redact before send** and route/escalate safely. Input handling separates raw ticket data from response template. | `src/validate/` (mandatory step on every generated response); `src/store` decision log; policy config in `src/config.py`/`docs/governance`. | `guardrail_checks_json`, `guardrail_action=blocked|redacted`, `guardrail_reason_text`, counts in metrics/governance report. |
| ND-02 | **Make unsupported claims or answer without grounding in retrieved corpus evidence** (including invented citations or citations that do not support the claim). | Hallucination, incorrect guidance, loss of trust; A4/A6 targets. | **Grounding/citation validation guardrail**: require answer claims to map to retrieved passage IDs; verify citations resolve to actually retrieved corpus passages; block or force "I don't know / escalate" when support is insufficient. Relevance threshold can return **no passages** rather than weak matches. | `src/retrieve/` (relevance threshold, source IDs), `src/generate/` (citation-structured output), `src/validate/` (claim/citation checks), `src/route/` (escalate on insufficient evidence). | `retrieval_results_json`, `citation_ids_json`, validation findings, route reason, A10 citation/hallucination metrics. |
| ND-03 | **Follow instructions embedded in customer/ticket text that attempt to override system behavior, reveal internals, bypass guardrails, or change policy** (prompt injection / instruction hierarchy violation). | Security/integrity failure, data exfiltration, policy bypass. | **Instruction-data separation**: ticket content treated as untrusted data in isolated context fields; fixed system/developer prompts; tool/output schemas constrain actions. **Prompt-injection/jailbreak detectors** in validation and/or pre-generation checks; block/escalate on detected override attempts. No execution of user-provided code/commands. | `src/ingest/` (normalize, tag untrusted content), `src/generate/` (prompt template boundaries), `src/validate/` (injection/policy checks), `src/route/`. | Guardrail check entries, blocked actions, route/escalation reasons in decision log. |
| ND-04 | **Auto-send a response when confidence/evidence/validation is insufficient** (low classification confidence, no relevant retrieval, guardrail uncertainty/failure). | Wrong answers to customers; A5 routing and governance targets. | **Deterministic routing threshold and safety gates**: escalate (or safe fallback) when `overall_confidence < threshold_used`, retrieval relevance below threshold, required citations missing, or validation cannot pass. "When in doubt, escalate with context" (summary + sources + uncertainty). | `src/route/` (threshold decision, deterministic), `src/validate/` (can block), `src/llm/` (timeouts/failure handling leading to safe fallback). | `route_decision`, `route_reason_text`, `threshold_used`, escalation payload, final action. |
| ND-05 | **Silently drop tickets or lose decision records** during single-ticket or unattended batch runs. | Operational failure, audit gaps; A8/A9. | **Harness-level accounting and reconciliation**: every input ticket gets a terminal outcome record (sent/escalated/blocked/failed_safe). Batch runner continues on per-ticket errors (A11) and records failures; end-of-run reconciliation compares processed/logged counts. | `evaluation/harness.py`, `src/store/` decision log, `src/graph.py` error handling. | `run_id` totals, per-ticket outcome rows, metrics report volume/reconciliation fields. |
| ND-06 | **Disable guardrails in evaluation/demo paths or bypass validation before release**. | False safety posture; A7 requires guardrails that can and do block. | **Single execution path through validation** for all generated responses; guardrail enablement controlled by explicit config defaults (on), tested in CI/unit tests; no "demo mode" bypass. | `src/validate/` pipeline integration, `src/config.py`, `tests/` (A7 trigger test). | Test evidence, guardrail activation logs, config/version recorded in decision log. |
| ND-07 | **Expose credentials, API keys, or secrets in code, logs, metrics, reports, or committed files**. | Security breach; explicit project rule. | **Secret hygiene controls**: `.env` gitignored, `.env.example` placeholders only, config loaded from env, log/exception scrubbing, CI/README checks for secret patterns. | `.gitignore`, `src/config.py`, logging setup, CI workflow, repo hygiene scripts/checks. | Secret-scan results, absence of secrets in committed artifacts. |
| ND-08 | **Crash or stop the full run on malformed input, no retrieval hit, provider timeout/outage, or rate limiting** (must degrade safely). | Availability/reliability failure; A11. | **Defensive input validation, typed fallbacks, retries with backoff, timeouts, circuit-breaker/offline fallback mode, and per-ticket exception containment** in batch harness. | `src/ingest/`, `src/retrieve/`, `src/llm/`, `src/graph.py`, `evaluation/harness.py`. | `error_flags_json`, `fallback_reason_text`, final action, run completion/report. |

## "Never do" statements (concise policy)
The system must never:
1. Send outbound content containing private/sensitive data or secrets.
2. Present unsupported claims or unverifiable/fabricated citations as grounded answers.
3. Obey or prioritize instructions contained in untrusted ticket/user content over system policy.
4. Auto-answer when evidence, confidence, or validation is insufficient; it must escalate or fail safely with context.
5. Drop a ticket or omit its decision record in batch/unattended processing.
6. Run with guardrails bypassed for responses that could be released.
7. Leak credentials/secrets through source, logs, or artifacts.
8. Halt the entire run due to a single-ticket or transient provider/input failure without a logged safe outcome.

## Review checklist
- [ ] Every "never do" item has at least one concrete, testable enforcement mechanism.
- [ ] Enforcement points are mapped to components/modules and not only prose intent.
- [ ] Guardrails can **block** (A7) and are on the release path (ND-06).
- [ ] Decision log captures enough evidence to audit each control (ND-01–ND-08).
- [ ] Risk register (T31, later) will link specific risks to these controls/mitigations.
