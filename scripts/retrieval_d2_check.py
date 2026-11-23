"""Checkpoint D2 / T18 verification: index build, reopen, search, and baseline hit-rate."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

# ensure project root importable when run as script
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_config  # noqa: E402
from src.retrieve.retriever import RetrievalIndex  # noqa: E402


def _pick_30_expected_doc_tickets(dev_tickets_path: Path):
    tickets = json.loads(dev_tickets_path.read_text(encoding="utf-8"))
    eligible = [t for t in tickets if (t.get("labels") or {}).get("expected_doc_ids")]
    rng = random.Random(42)
    if len(eligible) <= 30:
        return eligible
    return rng.sample(eligible, 30)


def main() -> int:
    config = get_config()
    idx = RetrievalIndex()
    meta = idx.build(force_rebuild=True)
    info1 = idx.info()

    # reopen/idempotent check
    idx2 = RetrievalIndex()
    loaded = idx2.load()
    info2 = idx2.info()

    sample_query = "How do I rotate API keys for my service account?"
    hits = idx2.search(sample_query, top_k=3)
    off_topic = idx2.search("best pizza recipe for weekend party", top_k=3, relevance_threshold=0.30)

    # baseline hit-rate on 30 dev tickets with expected_doc_ids
    sample_tickets = _pick_30_expected_doc_tickets(config.paths.data_dir / "development_tickets.json")
    evaluated = 0
    hits_count = 0
    details = []
    for t in sample_tickets:
        expected = list(((t.get("labels") or {}).get("expected_doc_ids")) or [])
        if not expected:
            continue
        query = f"{t.get('subject','')} {t.get('body','')}".strip()
        results = idx2.search(query, top_k=5)
        retrieved_doc_ids = []
        for r in results:
            if r.doc_id not in retrieved_doc_ids:
                retrieved_doc_ids.append(r.doc_id)
        ok = any(doc_id in retrieved_doc_ids for doc_id in expected)
        evaluated += 1
        hits_count += 1 if ok else 0
        details.append(
            {
                "ticket_id": t.get("ticket_id"),
                "expected_doc_ids": expected,
                "retrieved_doc_ids_top5": retrieved_doc_ids,
                "top_chunk_ids": [r.chunk_id for r in results[:3]],
                "top_scores": [round(r.score, 4) for r in results[:3]],
                "hit": ok,
            }
        )

    hit_rate = (hits_count / evaluated * 100.0) if evaluated else 0.0
    report = {
        "build_meta": meta,
        "info_after_build": info1,
        "reopened": loaded,
        "info_after_reopen": info2,
        "sample_query": sample_query,
        "sample_hits": [h.__dict__ for h in hits],
        "off_topic_query": "best pizza recipe for weekend party",
        "off_topic_hits_count": len(off_topic),
        "off_topic_hits": [h.__dict__ for h in off_topic],
        "baseline_30": {
            "evaluated": evaluated,
            "hits": hits_count,
            "hit_rate_percent": round(hit_rate, 2),
            "details": details,
        },
    }

    out_md = PROJECT_ROOT / "docs" / "workbooks" / "t18_retrieval_baseline.md"
    out_md.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("# T18 Retrieval Baseline (D2)")
    lines.append("")
    lines.append(f"- Backend: `{info2.get('backend')}`")
    lines.append(f"- Embedding: `{info2.get('embedding_model')}` (backend `{info2.get('embedding_backend')}`)")
    lines.append(f"- Corpus docs: {info2.get('doc_count')} | Chunks: {info2.get('chunk_count')}")
    lines.append(f"- Persist dir: `{info2.get('persist_dir')}`")
    lines.append(f"- Reopened successfully: `{loaded}`")
    lines.append(f"- Chunk IDs resolvable example: `{hits[0].chunk_id if hits else 'n/a'}`")
    lines.append(f"- Off-topic query returned empty at threshold {info2.get('relevance_threshold')}: `{len(off_topic) == 0}`")
    lines.append("")
    lines.append("## Baseline hit-rate (30 dev tickets with expected_doc_ids)")
    lines.append(f"- Evaluated: **{evaluated}**")
    lines.append(f"- Expected doc found in top-5 retrieved docs: **{hits_count}**")
    lines.append(f"- Hit-rate: **{hit_rate:.2f}%**")
    lines.append("")
    lines.append("## Sample retrieval")
    lines.append(f"Query: `{sample_query}`")
    for h in hits:
        lines.append(f"- rank {h.rank} score={h.score:.4f} chunk_id=`{h.chunk_id}` doc=`{h.doc_id}` title={h.title}")
        lines.append(f"  - resolvable text preview: {h.text[:120].replace(chr(10),' ')}...")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(report, ensure_ascii=False, indent=2)[:20000])
    lines.append("```")
    out_md.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "backend": info2.get("backend"),
        "embedding_backend": info2.get("embedding_backend"),
        "embedding_model": info2.get("embedding_model"),
        "doc_count": info2.get("doc_count"),
        "chunk_count": info2.get("chunk_count"),
        "reopened": loaded,
        "sample_hit_chunk": hits[0].chunk_id if hits else None,
        "sample_hit_resolvable": bool(idx2.resolve_chunk(hits[0].chunk_id)) if hits else False,
        "off_topic_empty": len(off_topic) == 0,
        "baseline_evaluated": evaluated,
        "baseline_hits": hits_count,
        "baseline_hit_rate_percent": round(hit_rate, 2),
        "report_path": str(out_md),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
