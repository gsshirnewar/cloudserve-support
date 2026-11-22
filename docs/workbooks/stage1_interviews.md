# Stage 1 — Stakeholder Interview Analysis (T03)

**Source:** [05_Datasets/Stakeholder_Interviews.docx](D:\FDE\IIT_Roorkee\FDE_Capstone_Complete\FDE_Capstone_Complete\Capstone_Pack\05_Datasets\Stakeholder_Interviews.docx) (extracted text)  
**Evidence register:** [evidence_register.csv](D:\FDE\IIT_Roorkee\FDE_Capstone_Complete\FDE_Capstone_Complete\Capstone_Pack\cloudserve-support\docs\workbooks\evidence_register.csv) (`EV-01`–`EV-28`)  
**Contradictions & data-test plans:** [contradictions.md](D:\FDE\IIT_Roorkee\FDE_Capstone_Complete\FDE_Capstone_Complete\Capstone_Pack\cloudserve-support\docs\workbooks\contradictions.md)

> Workbook mapping: this document covers **Stage 1 Discovery Workbook §Interviews** (who/role/context, key claims, quotes, evidence IDs). Quantitative verification and contradiction verdicts are planned for T04 using `development_tickets.json` only (validation set not used for tuning).

## Coverage summary
| # | Person | Role | Time with CloudServe / context | Interview length | Evidence IDs |
|---|---|---|---|---|---|
| 1 | Marcus Adeyemi | Head of Customer Support | 4 years; commissioned the work | 40 min (remote) | EV-01–EV-07 |
| 2 | Sofia Restrepo | Tier One Support Agent | 14 months; first-line volume | 35 min (remote) | EV-08–EV-13 |
| 3 | Daniel Okonkwo | Tier Two Support Engineer | 3 years; handles escalations | 30 min (remote) | EV-14–EV-18 |
| 4 | Ines Varga | Technical Writer (owns documentation) | 2 years; maintains KB | 25 min (remote) | EV-19–EV-22 |
| 5 | Ravi Menon | Customer, platform lead (mid-size client) | Customer for 2 years; raises tickets | 20 min (remote) | EV-23–EV-26 |

All five transcripts reviewed. Cross-cutting/context evidence from project docs captured as EV-27–EV-28.

## 1. Marcus Adeyemi — Head of Customer Support
**Why they matter:** Owns support numbers/budget and commissioned the work.

| Key claim | Quote (excerpt) | Evidence ID | Notes / follow-up |
|---|---|---|---|
| Support is overloaded; SLA (2h first response) is breached (8–12h avg). | "We take somewhere north of five hundred tickets a week now and we have six agents. Our service agreement says first response inside two hours and we are averaging somewhere between eight and twelve." | EV-01 | Validate against ticket history/baseline metrics in T04. |
| Prior interventions failed to scale (hiring, canned responses, outsourcing). | "We hired two people last year. It helped for about a month and then volume caught up. We tried a canned response library, which the agents hated because finding the right one took longer than writing the answer." | EV-02 | Solution must reduce effort/findability friction. |
| Wants "easy ones" answered so humans handle hard ones; improve response time without headcount. | "I picture it answering the easy ones so my people can do the hard ones... What I need is for the response time number to come down..." | EV-03 | Define "easy" via data (doc-answerable, low-risk, high-confidence). |
| FCR is the priority metric (42% now, 65% benchmark); escalations are costly. | "first contact resolution, if I am being honest, more than response time... every ticket that bounces to tier two costs us roughly four times what a resolved one costs..." | EV-04 | Compare to project target (≥60%) and baseline reconciliation. |
| Wrong customer-facing answers are unacceptable; automation must not increase agent work. | "If it sends something wrong to a customer... I would rather it said nothing than said something wrong. The second failure would be if it makes more work for the agents than it saves..." | EV-05 | Drives guardrails, calibration, escalation-with-context. |
| No clear ticket breakdown despite available data. | "If you asked me for a breakdown I would be guessing. We have the data, we have never really sat down with it." | EV-06 | Discovery must produce evidence-backed breakdown (T04). |
| Enterprise SLA sensitivity and compliance explainability requirements. | "Enterprise customers have a different agreement... And I have a compliance review in the autumn, so whatever we do has to be explainable..." | EV-07 | Tier segmentation + decision logging required. |

## 2. Sofia Restrepo — Tier One Support Agent
**Why they matter:** Handles first-line volume and sees tickets before anyone else.

| Key claim | Quote (excerpt) | Evidence ID | Notes / follow-up |
|---|---|---|---|
| High queue volume/pressure; oldest-first triage to avoid breaches. | "I open the queue and it is somewhere between forty and seventy tickets depending on the day. Mondays are worst. I sort by age because the oldest ones are the ones about to breach..." | EV-08 | Operational context for latency/priority. |
| ~70% of tickets are familiar/repetitive and could be answered quickly from experience. | "I would say seven out of ten I could answer without looking anything up, because I have answered the same question that month already. Password lockouts, rate limits, why is my invoice higher, my deployment keeps rolling back." | EV-09 | **Contradiction candidate (C1):** compare to FCR/escalation and answerable-from-docs labels. |
| Main time sink is finding/writing answers; KB search painful; agents rely on personal snippets. | "Finding it and writing it out. We have documentation, and it is good documentation, but searching it is painful, so most of us do not. I have a personal file of answers I have written before..." | EV-10 | Supports retrieval/findability intervention. |
| Escalates due to unknown answer, low confidence, or mandatory security cases. | "I do not know the answer. Or I think I know but I am not confident enough to send it... Or it is a security thing, which we are told to escalate every time regardless." | EV-11 | Distinguish avoidable vs policy-required escalations (C2). |
| Prefers assistive draft + relevant page; fears wrong auto-answers creating angry follow-ups. | "If it hands me a ticket with a draft and the relevant page attached, that would genuinely help... I am worried it will send a wrong answer..." | EV-12 | Escalation/draft payload is valuable outcome. |
| Non-fluent English customers take longer and have worse CSAT; may be unnoticed. | "The ones where English is not their first language take longer... Those tickets have our worst satisfaction scores and I do not think anyone has noticed." | EV-13 | **Contradiction/gap candidate (C3):** test by language_fluency segments. |

## 3. Daniel Okonkwo — Tier Two Support Engineer
**Why they matter:** Handles escalations and sees what tier one cannot resolve.

| Key claim | Quote (excerpt) | Evidence ID | Notes / follow-up |
|---|---|---|---|
| ~Half of escalations could be resolved by tier 1 (confidence/findability), not true complexity. | "In practice, about half of what reaches me is something tier one could have resolved if they had been confident, or if they had found the right page. The other half is genuinely hard..." | EV-14 | **Contradiction candidate (C2):** test avoidable escalation share in data. |
| Escalations arrive without summary/context/tried steps, causing rework. | "Usually just the original ticket, forwarded. No summary, no note about what was already tried..." | EV-15 | Design requirement for escalation package. |
| Wants escalation to show working: intent, relevant docs, uncertainty. | "here is the ticket, here is what I think it is about, here is the documentation that seemed relevant, and here is specifically what I was not confident about... I need it to show its working." | EV-16 | Aligns with decision log/routing transparency. |
| Risk of scaling outdated/wrong knowledge from current practices/snippet files. | "some of what we do now is wrong. There are answers circulating in people's personal snippet files... If you learn from those you will scale up a mistake." | EV-17 | Prefer curated KB grounding over imitation. |
| Some categories should not be auto-answered (security/compromise, billing disputes, data location). | "Anything touching security or account compromise... Billing disputes... And anything involving data location..." | EV-18 | Policy/guardrail constraints; compare with `must_not_auto_respond` labels. |

## 4. Ines Varga — Technical Writer (owns documentation)
**Why they matter:** Maintains the knowledge base the retrieval system will use.

| Key claim | Quote (excerpt) | Evidence ID | Notes / follow-up |
|---|---|---|---|
| 29 support KB articles cover repeated topics (auth, deployment, API, billing, data, security, account management). | "There are twenty-nine articles in the support knowledge base... They cover the things support answers repeatedly..." | EV-19 | Audit corpus coverage (T05). |
| Docs are used externally but underused internally due to keyword/title search mismatch (findability). | "Internally, I do not think the support team uses them at all... Our internal search matches on titles and exact terms, and customers do not describe problems in the words I used for the title." | EV-20 | Core mechanism for 'answer exists but not delivered'. |
| Private snippet files are unreviewed; retrieval should cite source articles for diagnosis. | "Every agent has a private file of answers and none of that has been reviewed by anyone... I would want to know which article an answer came from..." | EV-21 | Supports curated-corpus retrieval + citations (A4/A6). |
| Docs do not cover feature requests, roadmap/timing, or novel incidents; wrong answers in novel cases are high risk. | "Feature requests, obviously... Anything about roadmap or timing. And genuinely novel incidents... where a wrong answer does the most damage." | EV-22 | Automation limits; escalate/abstain when not grounded. |

## 5. Ravi Menon — Customer (platform lead, mid-size client)
**Why they matter:** Experiences current service and bears cost of delays/wrong answers.

| Key claim | Quote (excerpt) | Evidence ID | Notes / follow-up |
|---|---|---|---|
| Waiting is the main issue; impact varies by issue urgency/severity (same queue, different cost). | "Slow but decent once you get there. The waiting is the problem... If my deployment is failing at nine in the morning... four hours is a serious problem. Same queue, completely different cost to me." | EV-23 | Urgency-aware triage/response priority. |
| Customers self-search docs while waiting (~50% success) and often receive duplicate answers later. | "Search the documentation myself, usually. I find the answer maybe half the time. When I do find it, the reply that eventually arrives is normally the same thing..." | EV-24 | Validates value of fast, grounded first response. |
| Automated responses acceptable if honest, cited, and disclosed; confident wrong answers unacceptable. | "If it says here is what I think, here is the page it came from, and a person will confirm, that is useful... I would not accept is something that sounds certain and is wrong... I would want to know it was automated..." | EV-25 | Trust/calibration, citations, uncertainty disclosure. |
| Tier/plan service gaps are noticed and may affect renewal if widened. | "We are on the business plan... enterprise plan... gets answers in about an hour... if this change makes that gap bigger, we will notice..." | EV-26 | Fairness/tier segmentation in evaluation and governance. |

## Cross-cutting observations (for T04/T05/T07)
- **Repeated themes:** high wait/queue pressure, many repetitive questions, existing KB answers not effectively delivered/retrieved, escalations missing context, strong need for safe grounded responses and explainability.
- **Hypothesis to test:** a large share of tickets are answerable from existing documentation, but findability/confidence/process gaps prevent first-contact resolution (EV-09, EV-10, EV-14, EV-20, EV-24, EV-27).
- **Tensions to resolve in design:** fully automated chatbot request vs assistive/guarded automation and escalation-with-context (EV-03, EV-05, EV-12, EV-16, EV-25).
- **Data needed next (T04):** intent/urgency/channel/tier/region/language distributions, answerable-from-docs share, baseline FCR/escalation/response-time/CSAT, avoidable-escalation proxy, segment disparities, contradiction verdicts.
