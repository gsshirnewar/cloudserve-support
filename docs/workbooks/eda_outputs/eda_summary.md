# T04 EDA Summary (development_tickets.json)
- **Dataset:** `data/development_tickets.json` (development set only; validation set not opened)
- **Tickets analyzed:** 500
- **Documentation corpus (context):** 29 articles
## Overall baseline and volume signals
| Metric | Value |
|---|---:|
| Tickets | 500 |
| First contact resolution (%) | 43.8 |
| Escalation rate (%) | 56.2 |
| Repeat contact rate (%) | 21.6 |
| CSAT mean | 2.972 |
| CSAT median | 3.0 |
| Resolution time mean (minutes) | 421.7 |
| Resolution time median (minutes) | 214.0 |
| Answerable from docs (%) | 71.4 |
| Expected auto-respond (%) | 62.2 |

### Baseline comparison (brief/spec context)
- Brief reports first reply 8–12 hours, FCR 42%, escalation 58%, CSAT 3.2/5. The dev ticket `history` contains `resolution_time_minutes`, `first_contact_resolution`, `escalated`, `csat_rating` (not a direct first-reply timestamp field), so comparison below is based on available history fields.
- Observed (dev set): FCR **43.8%**, escalation **56.2%**, CSAT mean **2.972**, resolution median **214.0 min**. Any discrepancy vs brief figures should be explained in the workbook/report (population/sampling/definition differences).

## Contradiction verdicts (data-backed)
### C1 — Known/easy tickets vs outcomes (Sofia ~70% familiar)
- Answerable from docs: **357/500 (71.40%)**; expected auto-respond: **311/500 (62.20%)**.
- Among answerable-from-docs tickets: FCR **61.34%**, escalated **38.66%**, repeat contact **16.25%**.
- Among expected-auto-respond tickets: FCR **70.42%**, escalated **29.58%**.
- **Verdict:** Sofia's '7/10 seen before' perception is directionally supported if answerable/expected-auto shares are high, but historical outcomes show a substantial delivery gap (many doc-answerable/auto-routable tickets were not resolved/escalated). This supports a findability/retrieval/confidence and workflow problem, not merely absence of answers.

### C2 — Escalation composition (Daniel: ~half avoidable)
- Escalated tickets: **281/500 (56.20%)**.
- Escalated and answerable-from-docs: **138/281 (49.11%)**.
- Escalated and expected auto-respond: **92/281 (32.74%)**.
- Escalated and `must_not_auto_respond=false`: **194/281 (69.04%)**.
- **Avoidable-escalation proxy** (answerable + expected auto + not forced): **92/281 (32.74%)**.
- Avoidable proxy excluding sensitive-intent keywords (security/billing/data/account/compliance/privacy heuristic): **61/281 (21.71%)**.
- **Verdict (proxy-based):** A meaningful share of escalations appears potentially avoidable with better retrieval, confidence, and escalation context; compare proxy to Daniel's '~half' claim. This is a proxy (labels/history), not proof of tier-1 capability in each case.

### C3 — Segment differences (language fluency / tier / region)
| Segment | Tickets | FCR % | Escalation % | Repeat % | CSAT mean | CSAT median | Resolution median (min) |
|---|---:|---:|---:|---:|---:|---:|---:|
| language_fluency=fluent | 380 | 43.16 | 56.84 | 22.37 | 2.95 | 3.0 | 216.5 |
| language_fluency=non_fluent | 120 | 45.83 | 54.17 | 19.17 | 3.042 | 3.0 | 198.0 |
| customer_tier=business | 164 | 48.17 | 51.83 | 23.17 | 2.915 | 3.0 | 141.0 |
| customer_tier=enterprise | 83 | 37.35 | 62.65 | 24.1 | 3.048 | 3.0 | 369.0 |
| customer_tier=standard | 253 | 43.08 | 56.92 | 19.76 | 2.984 | 3.0 | 266.0 |
| customer_region=asia_pacific | 119 | 39.5 | 60.5 | 21.85 | 2.941 | 3.0 | 292.0 |
| customer_region=europe | 151 | 43.71 | 56.29 | 21.85 | 3.007 | 3.0 | 198.0 |
| customer_region=latin_america | 60 | 38.33 | 61.67 | 25.0 | 2.733 | 3.0 | 235.0 |
| customer_region=north_america | 170 | 48.82 | 51.18 | 20.0 | 3.047 | 3.0 | 109.5 |
- **Language fluency gap (fluent minus non_fluent):** CSAT mean Δ=-0.092, FCR Δ=-2.67 pp, escalation Δ=2.67 pp, resolution median Δ=18.5 min.
- **Verdict:** Segmentation provides evidence to test Sofia's concern and Ravi/Marcus tier concerns; interpret with sample sizes and intersection effects. These findings inform fairness audit hypotheses and triage/response design.

### C4 — KB adequacy vs access/delivery (findability)
- Documentation articles available: **29**; ticket intents observed: **22**.
- Tickets with `expected_doc_ids`: **357/500 (71.40%)**.
- Expected doc ID references not found in corpus: **0** (unique IDs: 0).
- Intents with zero tickets carrying `expected_doc_ids`: **2** (see `intent_doc_coverage.csv`; may indicate no-corpus/escalation intents).
- **Verdict:** Combined with C1/C2, evidence supports a delivery/findability gap: many tickets are labeled answerable/auto-routable yet historical outcomes underperform. Retrieval-grounded answers with citations and escalation for uncovered/sensitive cases align with transcripts and data.

## Reproducibility notes
- Script: `scripts/eda.py` (standard library only).
- Inputs: `data/development_tickets.json`, `data/documentation.json`.
- Excluded: `data/validation_tickets.json` (not opened/read).
- Outputs: CSV/MD files in `docs/workbooks/eda_outputs/` and `docs/workbooks/stage1_ticket_data.md`.
