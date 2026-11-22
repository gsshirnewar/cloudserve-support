# T05 — Documentation Corpus Audit

**Date:** 2026-11-22  
**Scope:** `cloudserve-support/data/documentation.json` (curated KB) audited against `data/development_tickets.json` (development set, 500 tickets) and T04 outputs (`eda_outputs/intent_doc_coverage.csv`, `answerable_from_docs.csv`). **`validation_tickets.json` was not opened or used.**  
**Evidence:** EV-35–EV-39 (see `docs/workbooks/t05_evidence_findings.csv`)

## 1. Article inventory (29 docs)

| Doc ID | Title | Category | Applies to | Content chars | Last reviewed (days ago) | Related docs |
|---|---|---|---:|---:|---:|---|
| DOC-AUTH-001 | Resolving invalid credential errors on login | auth | — | 1347 | 47 | DOC-AUTH-002 |
| DOC-AUTH-002 | Multi-factor authentication setup and recovery | auth | — | 1288 | 33 | DOC-AUTH-001 |
| DOC-AUTH-003 | Single sign-on configuration with SAML providers | auth | — | 1339 | 61 | DOC-ACCT-001 |
| DOC-AUTH-004 | API key rotation and scope management | auth | — | 1202 | 18 | DOC-SEC-002 |
| DOC-DEPLOY-001 | Container deployments failing during the health check phase | deploy | — | 1470 | 22 | DOC-DEPLOY-002, DOC-DEPLOY-004 |
| DOC-DEPLOY-002 | Rolling back a failed release | deploy | — | 1033 | 29 | DOC-DEPLOY-001 |
| DOC-DEPLOY-003 | Build failures caused by dependency resolution | deploy | — | 1224 | 54 | DOC-INT-001 |
| DOC-DEPLOY-004 | Configuring environment variables and secrets | deploy | — | 1253 | 14 | DOC-DEPLOY-001, DOC-SEC-002 |
| DOC-API-001 | Understanding API rate limits and quota tiers | api | — | 1258 | 9 | DOC-API-002, DOC-BILL-003 |
| DOC-API-002 | Pagination and handling large result sets | api | — | 1134 | 26 | DOC-API-001 |
| DOC-API-003 | Webhook delivery, retries and signature verification | api | — | 1230 | 41 | DOC-API-001, DOC-INT-002 |
| DOC-PERF-001 | Diagnosing elevated response latency | performance | — | 1347 | 38 | DOC-PERF-002, DOC-PERF-003 |
| DOC-PERF-002 | Autoscaling behaviour and instance limits | performance | — | 1182 | 52 | DOC-PERF-001 |
| DOC-PERF-003 | Database connection pool exhaustion | performance | — | 1267 | 11 | DOC-PERF-001, DOC-DATA-002 |
| DOC-BILL-001 | Understanding your invoice and usage breakdown | billing | — | 1180 | 7 | DOC-BILL-002, DOC-BILL-003 |
| DOC-BILL-002 | Changing plans, and how proration is calculated | billing | — | 1278 | 44 | DOC-BILL-001 |
| DOC-BILL-003 | Usage limits, overage and spend controls | billing | — | 1131 | 19 | DOC-BILL-001, DOC-API-001 |
| DOC-DATA-001 | Exporting account data and scheduled extracts | data | — | 1082 | 36 | DOC-DATA-002, DOC-SEC-003 |
| DOC-DATA-002 | Backups, retention and point-in-time restore | data | — | 1187 | 63 | DOC-DATA-001 |
| DOC-DATA-003 | Data residency and regional storage | data | — | 1218 | 28 | DOC-SEC-003 |
| DOC-SEC-001 | Responding to a suspected account compromise | security | — | 1140 | 16 | DOC-SEC-002, DOC-AUTH-002 |
| DOC-SEC-002 | Handling exposed secrets and credential rotation | security | — | 1175 | 21 | DOC-AUTH-004, DOC-SEC-001 |
| DOC-SEC-003 | Audit logging and compliance evidence | security | — | 1147 | 31 | DOC-DATA-001, DOC-DATA-003 |
| DOC-ACCT-001 | Managing team members, roles and permissions | account | — | 1115 | 24 | DOC-AUTH-003, DOC-ACCT-002 |
| DOC-ACCT-002 | Organisation setup and project structure | account | — | 1203 | 58 | DOC-ACCT-001 |
| DOC-INT-001 | Connecting continuous integration pipelines | integration | — | 1162 | 35 | DOC-DEPLOY-003, DOC-INT-002 |
| DOC-INT-002 | Third party monitoring and log forwarding | integration | — | 1197 | 49 | DOC-INT-001, DOC-API-003 |
| DOC-ONB-001 | First deployment: a walkthrough | onboarding | — | 953 | 12 | DOC-ONB-002, DOC-DEPLOY-001 |
| DOC-ONB-002 | Migrating an existing application to CloudServe | onboarding | — | 1117 | 27 | DOC-ONB-001, DOC-DATA-003 |

**Inventory notes:** Each article has `doc_id`, `title`, `category`, `applies_to` (list, empty in all current docs), `content` (single text blob), `related_docs`, and `last_reviewed_days_ago`. No `sections` field; content lengths range ~953–1470 chars (mean ~1199), suitable for small-chunk retrieval with metadata. `last_reviewed_days_ago` ranges 7–63 days (no obviously stale/outdated markers in content, but freshness should be surfaced in retrieval/governance).

## 2. Intent → doc coverage matrix (development tickets)

Source: development ticket labels (`intent`, `answerable_from_docs`, `expected_doc_ids`) joined to corpus. 357/500 tickets have `expected_doc_ids` (71.4%); **0 missing doc ID references**; **0 unreferenced docs** in corpus.

| Intent | Tickets | Answerable (%) | Tickets w/ expected doc IDs (%) | Doc refs (ticket-doc pairs) | Supporting doc IDs (count in expected_doc_ids) | No-doc intent? |
|---|---:|---:|---:|---:|---|---|
| account_access | 22 | 77.27 | 77.27 | 17 | DOC-ACCT-001 (17) | No |
| api_key_issue | 18 | 66.67 | 66.67 | 18 | DOC-AUTH-004 (12), DOC-SEC-002 (6) | No |
| api_usage_question | 24 | 95.83 | 95.83 | 33 | DOC-API-002 (23), DOC-API-003 (10) | No |
| authentication_failure | 20 | 70.00 | 70.00 | 18 | DOC-AUTH-001 (14), DOC-AUTH-002 (4) | No |
| billing_query | 24 | 87.50 | 87.50 | 32 | DOC-BILL-001 (21), DOC-BILL-002 (11) | No |
| compliance_request | 26 | 65.38 | 65.38 | 17 | DOC-SEC-003 (17) | No (but must not auto-respond by label) |
| configuration_help | 17 | 58.82 | 58.82 | 15 | DOC-DEPLOY-004 (10), DOC-ACCT-002 (5) | No |
| data_export | 29 | 93.10 | 93.10 | 27 | DOC-DATA-001 (27) | No |
| data_residency | 29 | 72.41 | 72.41 | 21 | DOC-DATA-003 (21) | No |
| database_issue | 26 | 69.23 | 69.23 | 26 | DOC-PERF-003 (18), DOC-DATA-002 (8) | No |
| deployment_failure | 27 | 70.37 | 70.37 | 24 | DOC-DEPLOY-001 (19), DOC-DEPLOY-003 (5) | No |
| **feature_request** | 20 | 0.00 | 0.00 | 0 | — | **Yes (must escalate by design)** |
| integration_help | 21 | 76.19 | 76.19 | 24 | DOC-INT-001 (16), DOC-INT-002 (8) | No |
| onboarding | 22 | 90.91 | 90.91 | 30 | DOC-ONB-001 (20), DOC-ONB-002 (10) | No |
| performance_degradation | 23 | 73.91 | 73.91 | 23 | DOC-PERF-001 (17), DOC-PERF-002 (6) | No |
| quota_or_overage | 23 | 86.96 | 86.96 | 32 | DOC-BILL-003 (20), DOC-API-001 (12) | No |
| rate_limit | 13 | 92.31 | 92.31 | 12 | DOC-API-001 (12) | No |
| rollback_request | 28 | 75.00 | 75.00 | 21 | DOC-DEPLOY-002 (21) | No |
| security_incident | 26 | 53.85 | 53.85 | 19 | DOC-SEC-001 (14), DOC-SEC-002 (5) | No (but must not auto-respond by label) |
| sso_configuration | 26 | 84.62 | 84.62 | 22 | DOC-AUTH-003 (22) | No |
| **unclear_request** | 15 | 0.00 | 0.00 | 0 | — | **Yes (must escalate/clarify by design)** |
| webhook_issue | 21 | 76.19 | 76.19 | 16 | DOC-API-003 (16) | No |

## 3. Coverage gaps and design implications

- **No supporting docs by design (must escalate/abstain):** `feature_request` (20 tickets) and `unclear_request` (15 tickets) have 0% answerable and 0 expected doc IDs. Routing/policy must not attempt grounded auto-resolution from KB for these intents.
- **Sensitive/high-risk intents with docs but restricted automation:** `security_incident`, `compliance_request` (and per labels `must_not_auto_respond=100%`) have corpus support but require human handling, evidence logging, and no autonomous resolution; retrieval may assist agents but not replace escalation/controls.
- **Partial doc linkage within answerable intents:** Some intents have fewer tickets with `expected_doc_ids` than total tickets (e.g. `account_access` 17/22, `configuration_help` 10/17, `database_issue` 18/26). This implies case-specific gaps, ambiguity, or need for clarification/retrieval confidence thresholds even when a relevant article exists.
- **Corpus integrity:** All referenced doc IDs exist in the corpus and every corpus doc is referenced by at least one development ticket intent mapping (no orphan docs, no dangling references in dev labels).
- **Stale/contradictory content:** No explicit contradictions detected from metadata alone; `last_reviewed_days_ago` (7–63) suggests periodic review is needed. Retrieval should include doc metadata (title/category/last reviewed) and citations to support verification and governance.

## 4. Chunking implications (hypothesis)

**Hypothesis:** Use **small, metadata-rich chunks** (e.g. ~300–600 characters or ~75–150 tokens) with **10–20% overlap**, one index entry per chunk carrying `doc_id`, `title`, `category`, `applies_to`, `related_docs`, `last_reviewed_days_ago`, and chunk position. Consider a **whole-document fallback chunk** for short articles.

**Rationale:**
- Articles are short single blobs (~953–1470 chars), so chunking is lightweight but still improves retrieval precision for multi-topic queries and citation granularity.
- Overlap reduces boundary loss (steps/conditions spanning chunk edges) without large index growth (29 docs).
- Rich metadata enables filtered retrieval/reranking by intent/category, link expansion via `related_docs`, and governance/audit traces (which doc/version reviewed when).
- For very short docs (<~1200 chars), whole-doc retrieval may perform similarly; chunking strategy should be validated against retrieval/citation quality in later evaluation (A4/ADR).

## 5. Stage 1 §Data & constraints (corpus)

- **Curated KB:** 29 articles across auth/deploy/api/performance/billing/data/security/account/integration/onboarding; all referenced by dev-ticket expected docs.
- **Constraints:** KB is the grounding source (no fabricated answers); `feature_request`/`unclear_request` and sensitive intents require escalation/abstention policies; doc freshness metadata must be preserved; retrieval/citations must be logged for traceability (A8).
- **Open validation:** Chunk size/overlap and retrieval thresholds to be decided/tested in design & evaluation phases using development data only.

## 6. Evidence mapping
- `EV-35`: Corpus inventory and schema/content characteristics (29 docs, fields, size/review ranges).
- `EV-36`: Intent→doc coverage matrix and integrity (all refs valid, no unreferenced docs).
- `EV-37`: No-doc intents and escalation-by-design gaps (`feature_request`, `unclear_request`).
- `EV-38`: Sensitive/partial-coverage implications (must-not-auto-respond intents, incomplete doc linkage).
- `EV-39`: Chunking hypothesis and rationale for retrieval design.
