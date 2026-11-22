# Stage 1 — Data & Constraints (Workbook Section)

**Last updated:** 2026-11-22 (T04–T05)  
**Evidence refs:** EV-29–EV-39 (see `evidence_register.csv` where available, `t04_evidence_findings.csv`, `t05_evidence_findings.csv`)

## Data assets (development/build scope)
| Asset | Location | Size / scope | Notes |
|---|---|---|---|
| Development tickets | `data/development_tickets.json` | 500 tickets | Used for discovery, EDA, design validation inputs; fields include channel, subject/body, timestamps, customer/tier/region/language_fluency, labels (intent, urgency, expected_route, answerable_from_docs, expected_doc_ids, must_not_auto_respond), history/outcomes. **Validation set not used.** |
| Validation tickets | `data/validation_tickets.json` | (held out) | **Do not open/tune on** during build/discovery per project rules; reserved for final evaluation/checkpoint. |
| Curated KB | `data/documentation.json` | 29 articles | Grounding corpus; fields: `doc_id,title,category,applies_to,content,related_docs,last_reviewed_days_ago`. Content ~953–1470 chars/article. |
| EDA outputs | `docs/workbooks/eda_outputs/*` | CSV/MD summaries | Reproducible via `python scripts/eda.py` (T04). |

## Key quantitative findings (T04, dev set)
- Baseline (n=500): FCR 43.8%, escalation 56.2%, repeat contact 21.6%, CSAT mean 2.972 (median 3.0), resolution mean 421.7 min / median 214.0 min. (`EV-29`)
- Answerable/routable labels: `answerable_from_docs` 71.4%, `expected_auto_respond` 62.2%, `must_not_auto_respond` 17.4% overall; broken down by channel/intent. (`EV-30`)
- Contradiction verdicts C1–C4: delivery/findability gap for answerable cases, avoidable-escalation proxy ~32.7% of escalations, mixed segment outcomes (no dev-set support for specific non-fluent-worse-CSAT claim), and corpus linkage supports KB adequacy with access/delivery gap. (`EV-31`–`EV-34`)

## Corpus coverage and gaps (T05)
- Intent→doc coverage mapped for all intents; 357/500 tickets have `expected_doc_ids`, 0 missing doc ID references, 0 unreferenced docs. (`EV-36`)
- **No supporting docs (must escalate/abstain by design):** `feature_request`, `unclear_request`. (`EV-37`)
- **Sensitive/restricted intents:** `security_incident`, `compliance_request` (and must-not-auto-respond cases) require human handling; retrieval may assist but must not auto-resolve. (`EV-38`)
- Partial doc linkage in some intents indicates need for confidence thresholds, clarification, and safe fallback.

## Constraints and guardrails
- **Grounding & safety:** Responses must be grounded in curated KB/citations; no fabricated claims; no PII/secret leakage; comply with `docs/governance/never_do.md` and decision logging schema (A7/A8/A11).
- **Privacy/compliance:** Treat ticket/customer content as sensitive; do not expose raw secrets/PII in logs or outputs; enforce redaction and access controls in implementation.
- **Provider/cost/runtime:** OpenRouter-first LLM configuration (`.env` local, gitignored); free-tier/latency/cost limits apply — design must favor efficient retrieval, bounded context, and fallbacks.
- **Data quality/labels:** Labels are provided in dev set; validation labels/ground truth must remain untouched until final evaluation; metrics definitions must be explicit (e.g. resolution minutes vs first-reply time).
- **Language/regions/segments:** Tickets span channels/tiers/regions/language fluency; segment disparities observed in dev EDA — fairness and calibration checks required later (avoid overfitting to any segment).

## Design implications
- Retrieval-augmented, citation-backed answering for doc-supported intents; confidence/intent/risk-aware routing to auto-answer, assist, or escalate.
- KB chunking/indexing to be implemented and evaluated (see corpus audit hypothesis EV-39); preserve metadata for traceability and freshness awareness.
- Explicit escalation paths for no-doc and must-not-auto-respond cases.
