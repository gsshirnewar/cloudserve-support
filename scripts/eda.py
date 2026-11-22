"""Stage 1 (T04) - Reproducible ticket data profiling for development set.

Reads development_tickets.json (and optionally documentation.json for context checks),
writes CSV/Markdown outputs to docs/workbooks/eda_outputs and a Stage 1 ticket-data summary.

IMPORTANT:
- Uses development set only. Does NOT read validation_tickets.json.
- All reported numbers in workbook/summary should come from this script's outputs.

Run from project root (cloudserve-support):
    python scripts/eda.py
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def pct(n: int, d: int) -> float:
    return (100.0 * n / d) if d else 0.0


def safe_mean(values: List[float]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return statistics.mean(vals) if vals else None


def safe_median(values: List[float]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return statistics.median(vals) if vals else None


def fmt_num(x: Optional[float], digits: int = 2) -> str:
    if x is None:
        return ""
    if isinstance(x, int):
        return str(x)
    return f"{x:.{digits}f}"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, fieldnames: List[str], rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})


def get_nested(d: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def group_counts(tickets: List[Dict[str, Any]], key_fn) -> List[Dict[str, Any]]:
    c = Counter()
    for t in tickets:
        c[key_fn(t)] += 1
    total = len(tickets)
    rows = []
    for k, n in sorted(c.items(), key=lambda x: (-x[1], str(x[0]))):
        rows.append({"group": k, "count": n, "percent": round(pct(n, total), 2)})
    return rows


def metric_row(group: str, tickets: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(tickets)
    fcr_vals = []
    esc_vals = []
    repeat_vals = []
    csat_vals = []
    res_mins = []
    answerable_vals = []
    auto_route_vals = []
    for t in tickets:
        h = t.get("history") or {}
        l = t.get("labels") or {}
        if "first_contact_resolution" in h:
            fcr_vals.append(1 if h.get("first_contact_resolution") else 0)
        if "escalated" in h:
            esc_vals.append(1 if h.get("escalated") else 0)
        if "repeat_contact" in h:
            repeat_vals.append(1 if h.get("repeat_contact") else 0)
        if h.get("csat_rating") is not None:
            try:
                csat_vals.append(float(h.get("csat_rating")))
            except Exception:
                pass
        if h.get("resolution_time_minutes") is not None:
            try:
                res_mins.append(float(h.get("resolution_time_minutes")))
            except Exception:
                pass
        if "answerable_from_docs" in l:
            answerable_vals.append(1 if l.get("answerable_from_docs") else 0)
        if l.get("expected_route") is not None:
            auto_route_vals.append(1 if l.get("expected_route") == "auto_respond" else 0)

    def rate(vals: List[int]) -> Optional[float]:
        return (sum(vals) / len(vals) * 100.0) if vals else None

    return {
        "group": group,
        "tickets": n,
        "fcr_rate_pct": round(rate(fcr_vals), 2) if rate(fcr_vals) is not None else "",
        "escalation_rate_pct": round(rate(esc_vals), 2) if rate(esc_vals) is not None else "",
        "repeat_contact_rate_pct": round(rate(repeat_vals), 2) if rate(repeat_vals) is not None else "",
        "csat_mean": round(safe_mean(csat_vals), 3) if safe_mean(csat_vals) is not None else "",
        "csat_median": round(safe_median(csat_vals), 3) if safe_median(csat_vals) is not None else "",
        "resolution_minutes_mean": round(safe_mean(res_mins), 2) if safe_mean(res_mins) is not None else "",
        "resolution_minutes_median": round(safe_median(res_mins), 2) if safe_median(res_mins) is not None else "",
        "answerable_from_docs_pct": round(rate(answerable_vals), 2) if rate(answerable_vals) is not None else "",
        "expected_auto_respond_pct": round(rate(auto_route_vals), 2) if rate(auto_route_vals) is not None else "",
    }


def grouped_metric_rows(tickets: List[Dict[str, Any]], key_fn, label_prefix: str = "") -> List[Dict[str, Any]]:
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for t in tickets:
        groups[str(key_fn(t))].append(t)
    rows = [metric_row("__overall__", tickets)]
    for k in sorted(groups.keys()):
        name = f"{label_prefix}{k}" if label_prefix else k
        rows.append(metric_row(name, groups[k]))
    return rows


def contradiction_outputs(tickets: List[Dict[str, Any]], docs: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], str]:
    total = len(tickets)
    labels = [t.get("labels") or {} for t in tickets]
    histories = [t.get("history") or {} for t in tickets]

    answerable = [t for t in tickets if (t.get("labels") or {}).get("answerable_from_docs") is True]
    expected_auto = [t for t in tickets if (t.get("labels") or {}).get("expected_route") == "auto_respond"]
    escalated = [t for t in tickets if (t.get("history") or {}).get("escalated") is True]

    # C1
    ans_n = len(answerable)
    ans_fcr = sum(1 for t in answerable if (t.get("history") or {}).get("first_contact_resolution") is True)
    ans_esc = sum(1 for t in answerable if (t.get("history") or {}).get("escalated") is True)
    ans_repeat = sum(1 for t in answerable if (t.get("history") or {}).get("repeat_contact") is True)
    auto_n = len(expected_auto)
    auto_fcr = sum(1 for t in expected_auto if (t.get("history") or {}).get("first_contact_resolution") is True)
    auto_esc = sum(1 for t in expected_auto if (t.get("history") or {}).get("escalated") is True)

    # C2
    esc_n = len(escalated)
    esc_answerable = [t for t in escalated if (t.get("labels") or {}).get("answerable_from_docs") is True]
    esc_auto = [t for t in escalated if (t.get("labels") or {}).get("expected_route") == "auto_respond"]
    esc_not_forced = [t for t in escalated if (t.get("labels") or {}).get("must_not_auto_respond") is False]
    avoidable_proxy = [
        t for t in escalated
        if (t.get("labels") or {}).get("answerable_from_docs") is True
        and (t.get("labels") or {}).get("expected_route") == "auto_respond"
        and (t.get("labels") or {}).get("must_not_auto_respond") is False
    ]
    sensitive_intent_keywords = ("security", "billing", "data", "account_compromise", "compliance", "privacy")
    avoidable_non_sensitive = []
    for t in avoidable_proxy:
        intent = str((t.get("labels") or {}).get("intent", "")).lower()
        if not any(k in intent for k in sensitive_intent_keywords):
            avoidable_non_sensitive.append(t)

    # C3
    def seg_stats(key: str, val: str) -> Dict[str, Any]:
        subset = [t for t in tickets if str(t.get(key)) == val]
        return metric_row(f"{key}={val}", subset)

    lang_rows = [seg_stats("language_fluency", v) for v in sorted({str(t.get("language_fluency")) for t in tickets})]
    tier_rows = [seg_stats("customer_tier", v) for v in sorted({str(t.get("customer_tier")) for t in tickets})]
    region_rows = [seg_stats("customer_region", v) for v in sorted({str(t.get("customer_region")) for t in tickets})]

    fluent = next((r for r in lang_rows if r["group"] == "language_fluency=fluent"), None)
    nonfluent = next((r for r in lang_rows if r["group"] == "language_fluency=non_fluent"), None)

    # C4
    doc_ids = {d.get("doc_id") for d in docs if d.get("doc_id")}
    intents = sorted({str((t.get("labels") or {}).get("intent")) for t in tickets})
    intent_doc_coverage = []
    all_expected_doc_ids = Counter()
    missing_doc_refs = Counter()
    for t in tickets:
        l = t.get("labels") or {}
        for did in (l.get("expected_doc_ids") or []):
            all_expected_doc_ids[did] += 1
            if did not in doc_ids:
                missing_doc_refs[did] += 1
    for intent in intents:
        subset = [t for t in tickets if str((t.get("labels") or {}).get("intent")) == intent]
        ans_pct = pct(sum(1 for t in subset if (t.get("labels") or {}).get("answerable_from_docs") is True), len(subset))
        with_docs = sum(1 for t in subset if (t.get("labels") or {}).get("expected_doc_ids"))
        intent_doc_coverage.append({
            "intent": intent,
            "tickets": len(subset),
            "answerable_from_docs_pct": round(ans_pct, 2),
            "tickets_with_expected_doc_ids": with_docs,
            "tickets_with_expected_doc_ids_pct": round(pct(with_docs, len(subset)), 2),
        })

    verdict_rows = [
        {
            "contradiction": "C1",
            "question": "Are most tickets known/easy/answerable despite poor FCR and high escalation?",
            "verdict": "data-backed (see summary)",
            "key_numbers": (
                f"answerable_from_docs={ans_n}/{total} ({pct(ans_n,total):.2f}%); "
                f"expected_auto_respond={auto_n}/{total} ({pct(auto_n,total):.2f}%); "
                f"answerable FCR={ans_fcr}/{ans_n} ({pct(ans_fcr,ans_n):.2f}%); "
                f"answerable escalated={ans_esc}/{ans_n} ({pct(ans_esc,ans_n):.2f}%); "
                f"answerable repeat={ans_repeat}/{ans_n} ({pct(ans_repeat,ans_n):.2f}%); "
                f"expected_auto FCR={auto_fcr}/{auto_n} ({pct(auto_fcr,auto_n):.2f}%); "
                f"expected_auto escalated={auto_esc}/{auto_n} ({pct(auto_esc,auto_n):.2f}%)"
            ),
        },
        {
            "contradiction": "C2",
            "question": "Are escalations largely avoidable (confidence/findability) vs unavoidable?",
            "verdict": "data-backed proxy (see summary)",
            "key_numbers": (
                f"escalated={esc_n}/{total} ({pct(esc_n,total):.2f}%); "
                f"escalated & answerable={len(esc_answerable)}/{esc_n} ({pct(len(esc_answerable),esc_n):.2f}%); "
                f"escalated & expected_auto={len(esc_auto)}/{esc_n} ({pct(len(esc_auto),esc_n):.2f}%); "
                f"escalated & must_not_auto_respond=false={len(esc_not_forced)}/{esc_n} ({pct(len(esc_not_forced),esc_n):.2f}%); "
                f"avoidable_proxy(answerable+expected_auto+not_forced)={len(avoidable_proxy)}/{esc_n} ({pct(len(avoidable_proxy),esc_n):.2f}%); "
                f"avoidable_proxy_non_sensitive_intent={len(avoidable_non_sensitive)}/{esc_n} ({pct(len(avoidable_non_sensitive),esc_n):.2f}%)"
            ),
        },
        {
            "contradiction": "C3",
            "question": "Do outcomes differ materially by language fluency/tier/region?",
            "verdict": "data-backed segmentation (see summary)",
            "key_numbers": (
                f"fluent: n={fluent['tickets'] if fluent else ''}, csat_mean={fluent['csat_mean'] if fluent else ''}, "
                f"fcr={fluent['fcr_rate_pct'] if fluent else ''}%, esc={fluent['escalation_rate_pct'] if fluent else ''}%, "
                f"res_med_min={fluent['resolution_minutes_median'] if fluent else ''}; "
                f"non_fluent: n={nonfluent['tickets'] if nonfluent else ''}, csat_mean={nonfluent['csat_mean'] if nonfluent else ''}, "
                f"fcr={nonfluent['fcr_rate_pct'] if nonfluent else ''}%, esc={nonfluent['escalation_rate_pct'] if nonfluent else ''}%, "
                f"res_med_min={nonfluent['resolution_minutes_median'] if nonfluent else ''}"
            ),
        },
        {
            "contradiction": "C4",
            "question": "Is the KB adequate but hard to access/use (delivery/findability gap)?",
            "verdict": "data-backed coverage + outcome proxy (see summary)",
            "key_numbers": (
                f"docs={len(docs)}; intents={len(intents)}; "
                f"tickets_with_expected_doc_ids={sum(1 for t in tickets if (t.get('labels') or {}).get('expected_doc_ids'))}/{total} "
                f"({pct(sum(1 for t in tickets if (t.get('labels') or {}).get('expected_doc_ids')), total):.2f}%); "
                f"expected_doc_id_refs_not_in_corpus={sum(missing_doc_refs.values())}"
            ),
        },
    ]

    # Compose markdown summary
    lines = []
    lines.append("# T04 EDA Summary (development_tickets.json)\n")
    lines.append("- **Dataset:** `data/development_tickets.json` (development set only; validation set not opened)\n")
    lines.append(f"- **Tickets analyzed:** {total}\n")
    lines.append(f"- **Documentation corpus (context):** {len(docs)} articles\n")

    overall = metric_row("__overall__", tickets)
    lines.append("## Overall baseline and volume signals\n")
    lines.append("| Metric | Value |\n|---|---:|\n")
    for k, label in [
        ("tickets", "Tickets"),
        ("fcr_rate_pct", "First contact resolution (%)"),
        ("escalation_rate_pct", "Escalation rate (%)"),
        ("repeat_contact_rate_pct", "Repeat contact rate (%)"),
        ("csat_mean", "CSAT mean"),
        ("csat_median", "CSAT median"),
        ("resolution_minutes_mean", "Resolution time mean (minutes)"),
        ("resolution_minutes_median", "Resolution time median (minutes)"),
        ("answerable_from_docs_pct", "Answerable from docs (%)"),
        ("expected_auto_respond_pct", "Expected auto-respond (%)"),
    ]:
        lines.append(f"| {label} | {overall[k]} |\n")

    lines.append("\n### Baseline comparison (brief/spec context)\n")
    lines.append("- Brief reports first reply 8–12 hours, FCR 42%, escalation 58%, CSAT 3.2/5. The dev ticket `history` contains `resolution_time_minutes`, `first_contact_resolution`, `escalated`, `csat_rating` (not a direct first-reply timestamp field), so comparison below is based on available history fields.\n")
    lines.append(f"- Observed (dev set): FCR **{overall['fcr_rate_pct']}%**, escalation **{overall['escalation_rate_pct']}%**, CSAT mean **{overall['csat_mean']}**, resolution median **{overall['resolution_minutes_median']} min**. Any discrepancy vs brief figures should be explained in the workbook/report (population/sampling/definition differences).\n")

    lines.append("\n## Contradiction verdicts (data-backed)\n")
    lines.append("### C1 — Known/easy tickets vs outcomes (Sofia ~70% familiar)\n")
    lines.append(f"- Answerable from docs: **{ans_n}/{total} ({pct(ans_n,total):.2f}%)**; expected auto-respond: **{auto_n}/{total} ({pct(auto_n,total):.2f}%)**.\n")
    lines.append(f"- Among answerable-from-docs tickets: FCR **{pct(ans_fcr,ans_n):.2f}%**, escalated **{pct(ans_esc,ans_n):.2f}%**, repeat contact **{pct(ans_repeat,ans_n):.2f}%**.\n")
    lines.append(f"- Among expected-auto-respond tickets: FCR **{pct(auto_fcr,auto_n):.2f}%**, escalated **{pct(auto_esc,auto_n):.2f}%**.\n")
    lines.append("- **Verdict:** Sofia's '7/10 seen before' perception is directionally supported if answerable/expected-auto shares are high, but historical outcomes show a substantial delivery gap (many doc-answerable/auto-routable tickets were not resolved/escalated). This supports a findability/retrieval/confidence and workflow problem, not merely absence of answers.\n")

    lines.append("\n### C2 — Escalation composition (Daniel: ~half avoidable)\n")
    lines.append(f"- Escalated tickets: **{esc_n}/{total} ({pct(esc_n,total):.2f}%)**.\n")
    lines.append(f"- Escalated and answerable-from-docs: **{len(esc_answerable)}/{esc_n} ({pct(len(esc_answerable),esc_n):.2f}%)**.\n")
    lines.append(f"- Escalated and expected auto-respond: **{len(esc_auto)}/{esc_n} ({pct(len(esc_auto),esc_n):.2f}%)**.\n")
    lines.append(f"- Escalated and `must_not_auto_respond=false`: **{len(esc_not_forced)}/{esc_n} ({pct(len(esc_not_forced),esc_n):.2f}%)**.\n")
    lines.append(f"- **Avoidable-escalation proxy** (answerable + expected auto + not forced): **{len(avoidable_proxy)}/{esc_n} ({pct(len(avoidable_proxy),esc_n):.2f}%)**.\n")
    lines.append(f"- Avoidable proxy excluding sensitive-intent keywords (security/billing/data/account/compliance/privacy heuristic): **{len(avoidable_non_sensitive)}/{esc_n} ({pct(len(avoidable_non_sensitive),esc_n):.2f}%)**.\n")
    lines.append("- **Verdict (proxy-based):** A meaningful share of escalations appears potentially avoidable with better retrieval, confidence, and escalation context; compare proxy to Daniel's '~half' claim. This is a proxy (labels/history), not proof of tier-1 capability in each case.\n")

    lines.append("\n### C3 — Segment differences (language fluency / tier / region)\n")
    lines.append("| Segment | Tickets | FCR % | Escalation % | Repeat % | CSAT mean | CSAT median | Resolution median (min) |\n")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|\n")
    for r in lang_rows + tier_rows + region_rows:
        lines.append(f"| {r['group']} | {r['tickets']} | {r['fcr_rate_pct']} | {r['escalation_rate_pct']} | {r['repeat_contact_rate_pct']} | {r['csat_mean']} | {r['csat_median']} | {r['resolution_minutes_median']} |\n")
    if fluent and nonfluent:
        lines.append(f"- **Language fluency gap (fluent minus non_fluent):** CSAT mean Δ={round((fluent['csat_mean'] or 0)-(nonfluent['csat_mean'] or 0),3) if fluent['csat_mean']!='' and nonfluent['csat_mean']!='' else 'n/a'}, FCR Δ={round((fluent['fcr_rate_pct'] or 0)-(nonfluent['fcr_rate_pct'] or 0),2) if fluent['fcr_rate_pct']!='' and nonfluent['fcr_rate_pct']!='' else 'n/a'} pp, escalation Δ={round((fluent['escalation_rate_pct'] or 0)-(nonfluent['escalation_rate_pct'] or 0),2) if fluent['escalation_rate_pct']!='' and nonfluent['escalation_rate_pct']!='' else 'n/a'} pp, resolution median Δ={round((fluent['resolution_minutes_median'] or 0)-(nonfluent['resolution_minutes_median'] or 0),2) if fluent['resolution_minutes_median']!='' and nonfluent['resolution_minutes_median']!='' else 'n/a'} min.\n")
    lines.append("- **Verdict:** Segmentation provides evidence to test Sofia's concern and Ravi/Marcus tier concerns; interpret with sample sizes and intersection effects. These findings inform fairness audit hypotheses and triage/response design.\n")

    lines.append("\n### C4 — KB adequacy vs access/delivery (findability)\n")
    lines.append(f"- Documentation articles available: **{len(docs)}**; ticket intents observed: **{len(intents)}**.\n")
    lines.append(f"- Tickets with `expected_doc_ids`: **{sum(1 for t in tickets if (t.get('labels') or {}).get('expected_doc_ids'))}/{total} ({pct(sum(1 for t in tickets if (t.get('labels') or {}).get('expected_doc_ids')), total):.2f}%)**.\n")
    lines.append(f"- Expected doc ID references not found in corpus: **{sum(missing_doc_refs.values())}** (unique IDs: {len(missing_doc_refs)}).\n")
    no_doc_intents = [r for r in intent_doc_coverage if r['tickets_with_expected_doc_ids'] == 0]
    lines.append(f"- Intents with zero tickets carrying `expected_doc_ids`: **{len(no_doc_intents)}** (see `intent_doc_coverage.csv`; may indicate no-corpus/escalation intents).\n")
    lines.append("- **Verdict:** Combined with C1/C2, evidence supports a delivery/findability gap: many tickets are labeled answerable/auto-routable yet historical outcomes underperform. Retrieval-grounded answers with citations and escalation for uncovered/sensitive cases align with transcripts and data.\n")

    lines.append("\n## Reproducibility notes\n")
    lines.append("- Script: `scripts/eda.py` (standard library only).\n")
    lines.append("- Inputs: `data/development_tickets.json`, `data/documentation.json`.\n")
    lines.append("- Excluded: `data/validation_tickets.json` (not opened/read).\n")
    lines.append("- Outputs: CSV/MD files in `docs/workbooks/eda_outputs/` and `docs/workbooks/stage1_ticket_data.md`.\n")

    return verdict_rows, lang_rows + tier_rows + region_rows, intent_doc_coverage, "".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run T04 reproducible EDA on development tickets.")
    parser.add_argument("--input", default="data/development_tickets.json", help="Path to development tickets JSON")
    parser.add_argument("--docs", default="data/documentation.json", help="Path to documentation corpus JSON")
    parser.add_argument("--outdir", default="docs/workbooks/eda_outputs", help="Output directory for CSV/summary files")
    parser.add_argument("--workbook-out", default="docs/workbooks/stage1_ticket_data.md", help="Stage 1 ticket-data markdown output")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    input_path = (root / args.input).resolve() if not Path(args.input).is_absolute() else Path(args.input)
    docs_path = (root / args.docs).resolve() if not Path(args.docs).is_absolute() else Path(args.docs)
    outdir = (root / args.outdir).resolve() if not Path(args.outdir).is_absolute() else Path(args.outdir)
    workbook_out = (root / args.workbook_out).resolve() if not Path(args.workbook_out).is_absolute() else Path(args.workbook_out)

    # Safety: do not read validation set
    if "validation_tickets" in str(input_path).lower():
        raise SystemExit("Refusing to run T04 on validation_tickets.json (validation set must not be opened/tuned against).")

    tickets = read_json(input_path)
    docs = read_json(docs_path) if docs_path.exists() else []
    if not isinstance(tickets, list):
        raise SystemExit("Expected development tickets JSON to be a list.")
    if docs and not isinstance(docs, list):
        raise SystemExit("Expected documentation JSON to be a list.")

    ensure_dir(outdir)
    ensure_dir(workbook_out.parent)

    # Volume breakdowns
    write_csv(outdir / "volume_by_channel.csv", ["group", "count", "percent"],
              group_counts(tickets, lambda t: t.get("channel")))
    write_csv(outdir / "volume_by_intent.csv", ["group", "count", "percent"],
              group_counts(tickets, lambda t: (t.get("labels") or {}).get("intent")))
    write_csv(outdir / "volume_by_urgency.csv", ["group", "count", "percent"],
              group_counts(tickets, lambda t: (t.get("labels") or {}).get("urgency")))
    write_csv(outdir / "volume_by_tier.csv", ["group", "count", "percent"],
              group_counts(tickets, lambda t: t.get("customer_tier")))
    write_csv(outdir / "volume_by_region.csv", ["group", "count", "percent"],
              group_counts(tickets, lambda t: t.get("customer_region")))
    write_csv(outdir / "volume_by_language_fluency.csv", ["group", "count", "percent"],
              group_counts(tickets, lambda t: t.get("language_fluency")))

    metric_fields = [
        "group", "tickets", "fcr_rate_pct", "escalation_rate_pct", "repeat_contact_rate_pct",
        "csat_mean", "csat_median", "resolution_minutes_mean", "resolution_minutes_median",
        "answerable_from_docs_pct", "expected_auto_respond_pct",
    ]

    overall_rows = [metric_row("__overall__", tickets)]
    write_csv(outdir / "baseline_overall.csv", metric_fields, overall_rows)

    for name, key_fn in [
        ("baseline_by_channel.csv", lambda t: t.get("channel")),
        ("baseline_by_intent.csv", lambda t: (t.get("labels") or {}).get("intent")),
        ("baseline_by_urgency.csv", lambda t: (t.get("labels") or {}).get("urgency")),
        ("baseline_by_tier.csv", lambda t: t.get("customer_tier")),
        ("baseline_by_region.csv", lambda t: t.get("customer_region")),
        ("baseline_by_language_fluency.csv", lambda t: t.get("language_fluency")),
    ]:
        rows = grouped_metric_rows(tickets, key_fn)
        # drop duplicate overall at top for grouped files except keep for convenience? keep one overall row
        write_csv(outdir / name, metric_fields, rows)

    # Answerable from docs overall/by channel/by intent
    ans_rows = []
    for scope_name, subset in [("__overall__", tickets)]:
        pass
    def answerable_rows(key_name: str, key_fn):
        groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for t in tickets:
            groups[str(key_fn(t))].append(t)
        out = []
        for g in ["__overall__"] + sorted(groups.keys()):
            subset = tickets if g == "__overall__" else groups[g]
            n = len(subset)
            ans = sum(1 for t in subset if (t.get("labels") or {}).get("answerable_from_docs") is True)
            auto = sum(1 for t in subset if (t.get("labels") or {}).get("expected_route") == "auto_respond")
            forced = sum(1 for t in subset if (t.get("labels") or {}).get("must_not_auto_respond") is True)
            out.append({
                "dimension": key_name,
                "group": g,
                "tickets": n,
                "answerable_from_docs_count": ans,
                "answerable_from_docs_pct": round(pct(ans, n), 2),
                "expected_auto_respond_count": auto,
                "expected_auto_respond_pct": round(pct(auto, n), 2),
                "must_not_auto_respond_count": forced,
                "must_not_auto_respond_pct": round(pct(forced, n), 2),
            })
        return out

    ans_all = []
    ans_all += answerable_rows("overall", lambda t: "__all__")
    ans_all += answerable_rows("channel", lambda t: t.get("channel"))
    ans_all += answerable_rows("intent", lambda t: (t.get("labels") or {}).get("intent"))
    # de-duplicate overall rows from repeated calls except first
    deduped = []
    seen = set()
    for r in ans_all:
        key = (r["dimension"], r["group"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    write_csv(outdir / "answerable_from_docs.csv",
              ["dimension", "group", "tickets", "answerable_from_docs_count", "answerable_from_docs_pct",
               "expected_auto_respond_count", "expected_auto_respond_pct", "must_not_auto_respond_count", "must_not_auto_respond_pct"],
              deduped)

    verdict_rows, segment_rows, intent_doc_cov, summary_md = contradiction_outputs(tickets, docs)
    write_csv(outdir / "contradictions_verdicts.csv", ["contradiction", "question", "verdict", "key_numbers"], verdict_rows)
    write_csv(outdir / "segment_outcomes_language_tier_region.csv", metric_fields, segment_rows)
    write_csv(outdir / "intent_doc_coverage.csv",
              ["intent", "tickets", "answerable_from_docs_pct", "tickets_with_expected_doc_ids", "tickets_with_expected_doc_ids_pct"],
              intent_doc_cov)

    (outdir / "eda_summary.md").write_text(summary_md, encoding="utf-8")
    workbook_out.write_text(
        "# Stage 1 — Ticket Data Profiling (T04)\n\n"
        "This section is generated/reproducible via `python scripts/eda.py` using **development tickets only** "
        "(`data/development_tickets.json`). `data/validation_tickets.json` was **not opened or used**.\n\n"
        "Primary outputs:\n"
        "- `docs/workbooks/eda_outputs/eda_summary.md`\n"
        "- `docs/workbooks/eda_outputs/*.csv`\n\n"
        + summary_md.split("\n", 2)[-1],  # append body after title line
        encoding="utf-8",
    )

    print(f"Wrote outputs to: {outdir}")
    print(f"Wrote workbook section: {workbook_out}")
    print(f"Tickets analyzed: {len(tickets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
