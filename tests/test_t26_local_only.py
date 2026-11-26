from evaluation.t26_local_only import _confidence_sweep, _score_retrieval_threshold


def test_retrieval_threshold_metrics_compare_expected_documents():
    examples = [
        {
            "expected_docs": ["DOC-A"],
            "hits": [
                {"doc_id": "DOC-A", "score": 0.8},
                {"doc_id": "DOC-B", "score": 0.6},
            ],
        },
        {
            "expected_docs": ["DOC-B"],
            "hits": [{"doc_id": "DOC-A", "score": 0.9}],
        },
    ]

    metrics = _score_retrieval_threshold(examples, 0.7)

    assert metrics["query_coverage"] == 1.0
    assert metrics["ticket_hit_rate"] == 0.5
    assert metrics["doc_precision"] == 0.5
    assert metrics["doc_recall"] == 0.5
    assert metrics["doc_f1"] == 0.5


def test_confidence_sweep_excludes_fallback_predictions():
    tickets = [{"labels": {"expected_route": "auto_respond"}}]
    records = {
        0: {
            "result": {
                "classification": {
                    "fallback_used": True,
                    "overall_confidence": 1.0,
                },
            },
        },
    }

    sweep = _confidence_sweep(tickets, records)

    assert all(row["auto_candidate_count"] == 0 for row in sweep)
    assert all(row["wrong_route_rate"] is None for row in sweep)
