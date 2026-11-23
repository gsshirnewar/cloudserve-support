# T18 Retrieval Baseline (D2)

- Backend: `local`
- Embedding: `sentence-transformers/all-MiniLM-L6-v2 (hash-fallback)` (backend `hash_fallback`)
- Corpus docs: 29 | Chunks: 90
- Persist dir: `D:\FDE\IIT_Roorkee\FDE_Capstone_Complete\FDE_Capstone_Complete\Capstone_Pack\cloudserve-support\storage\chroma`
- Reopened successfully: `True`
- Chunk IDs resolvable example: `n/a`
- Off-topic query returned empty at threshold 0.3: `True`

## Baseline hit-rate (30 dev tickets with expected_doc_ids)
- Evaluated: **30**
- Expected doc found in top-5 retrieved docs: **15**
- Hit-rate: **50.00%**

## Sample retrieval
Query: `How do I rotate API keys for my service account?`

```json
{
  "build_meta": {
    "backend": "local",
    "corpus_path": "D:\\FDE\\IIT_Roorkee\\FDE_Capstone_Complete\\FDE_Capstone_Complete\\Capstone_Pack\\cloudserve-support\\data\\documentation.json",
    "doc_count": 29,
    "chunk_count": 90,
    "chunk_size": 500,
    "chunk_overlap": 80,
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2 (hash-fallback)",
    "embedding_dimension": 384,
    "embedding_backend": "hash_fallback"
  },
  "info_after_build": {
    "backend": "local",
    "corpus_path": "D:\\FDE\\IIT_Roorkee\\FDE_Capstone_Complete\\FDE_Capstone_Complete\\Capstone_Pack\\cloudserve-support\\data\\documentation.json",
    "doc_count": 29,
    "chunk_count": 90,
    "chunk_size": 500,
    "chunk_overlap": 80,
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2 (hash-fallback)",
    "embedding_dimension": 384,
    "embedding_backend": "hash_fallback",
    "persist_dir": "D:\\FDE\\IIT_Roorkee\\FDE_Capstone_Complete\\FDE_Capstone_Complete\\Capstone_Pack\\cloudserve-support\\storage\\chroma",
    "relevance_threshold": 0.3,
    "ready": true,
    "chunk_ids": 90
  },
  "reopened": true,
  "info_after_reopen": {
    "backend": "local",
    "corpus_path": "D:\\FDE\\IIT_Roorkee\\FDE_Capstone_Complete\\FDE_Capstone_Complete\\Capstone_Pack\\cloudserve-support\\data\\documentation.json",
    "doc_count": 29,
    "chunk_count": 90,
    "chunk_size": 500,
    "chunk_overlap": 80,
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2 (hash-fallback)",
    "embedding_dimension": 384,
    "embedding_backend": "hash_fallback",
    "persist_dir": "D:\\FDE\\IIT_Roorkee\\FDE_Capstone_Complete\\FDE_Capstone_Complete\\Capstone_Pack\\cloudserve-support\\storage\\chroma",
    "relevance_threshold": 0.3,
    "ready": true,
    "chunk_ids": 90
  },
  "sample_query": "How do I rotate API keys for my service account?",
  "sample_hits": [],
  "off_topic_query": "best pizza recipe for weekend party",
  "off_topic_hits_count": 0,
  "off_topic_hits": [],
  "baseline_30": {
    "evaluated": 30,
    "hits": 15,
    "hit_rate_percent": 50.0,
    "details": [
      {
        "ticket_id": "DEV-0462",
        "expected_doc_ids": [
          "DOC-ONB-001"
        ],
        "retrieved_doc_ids_top5": [
          "DOC-ONB-001",
          "DOC-DEPLOY-003",
          "DOC-BILL-001",
          "DOC-SEC-002"
        ],
        "top_chunk_ids": [
          "DOC-ONB-001#chunk_1",
          "DOC-DEPLOY-003#chunk_1",
          "DOC-BILL-001#chunk_0"
        ],
        "top_scores": [
          0.4183,
          0.4156,
          0.4113
        ],
        "hit": true
      },
      {
        "ticket_id": "DEV-0080",
        "expected_doc_ids": [
          "DOC-API-003"
        ],
        "retrieved_doc_ids_top5": [
          "DOC-API-003",
          "DOC-BILL-002",
          "DOC-BILL-001",
          "DOC-AUTH-003"
        ],
        "top_chunk_ids": [
          "DOC-API-003#chunk_0",
          "DOC-API-003#chunk_1",
          "DOC-BILL-002#chunk_1"
        ],
        "top_scores": [
          0.6275,
          0.5658,
          0.4778
        ],
        "hit": true
      },
      {
        "ticket_id": "DEV-0018",
        "expected_doc_ids": [
          "DOC-API-002",
          "DOC-API-003"
        ],
        "retrieved_doc_ids_top5": [],
        "top_chunk_ids": [],
        "top_scores": [],
        "hit": false
      },
      {
        "ticket_id": "DEV-0208",
        "expected_doc_ids": [
          "DOC-DATA-003"
        ],
        "retrieved_doc_ids_top5": [
          "DOC-DATA-003"
        ],
        "top_chunk_ids": [
          "DOC-DATA-003#chunk_0"
        ],
        "top_scores": [
          0.3177
        ],
        "hit": true
      },
      {
        "ticket_id": "DEV-0189",
        "expected_doc_ids": [
          "DOC-BILL-001",
          "DOC-BILL-002"
        ],
        "retrieved_doc_ids_top5": [
          "DOC-ONB-001",
          "DOC-SEC-001"
        ],
        "top_chunk_ids": [
          "DOC-ONB-001#chunk_0",
          "DOC-SEC-001#chunk_0"
        ],
        "top_scores": [
          0.3119,
          0.3114
        ],
        "hit": false
      },
      {
        "ticket_id": "DEV-0174",
        "expected_doc_ids": [
          "DOC-ONB-001",
          "DOC-ONB-002"
        ],
        "retrieved_doc_ids_top5": [
          "DOC-AUTH-003",
          "DOC-ONB-002"
        ],
        "top_chunk_ids": [
          "DOC-AUTH-003#chunk_0",
          "DOC-ONB-002#chunk_2"
        ],
        "top_scores": [
          0.3381,
          0.3108
        ],
        "hit": true
      },
      {
        "ticket_id": "DEV-0100",
        "expected_doc_ids": [
          "DOC-API-001"
        ],
        "retrieved_doc_ids_top5": [],
        "top_chunk_ids": [],
        "top_scores": [],
        "hit": false
      },
      {
        "ticket_id": "DEV-0072",
        "expected_doc_ids": [
          "DOC-DEPLOY-001"
        ],
        "retrieved_doc_ids_top5": [
          "DOC-DEPLOY-001",
          "DOC-API-003",
          "DOC-BILL-001",
          "DOC-SEC-001"
        ],
        "top_chunk_ids": [
          "DOC-DEPLOY-001#chunk_0",
          "DOC-API-003#chunk_1",
          "DOC-DEPLOY-001#chunk_2"
        ],
        "top_scores": [
          0.4858,
          0.3892,
          0.3788
        ],
        "hit": true
      },
      {
        "ticket_id": "DEV-0485",
        "expected_doc_ids": [
          "DOC-ACCT-001"
        ],
        "retrieved_doc_ids_top5": [
          "DOC-ACCT-001",
          "DOC-ONB-001",
          "DOC-ONB-002",
          "DOC-ACCT-002",
          "DOC-AUTH-004"
        ],
        "top_chunk_ids": [
          "DOC-ACCT-001#chunk_0",
          "DOC-ONB-001#chunk_0",
          "DOC-ONB-002#chunk_2"
        ],
        "top_scores": [
          0.4591,
          0.4086,
          0.3617
        ],
        "hit": true
      },
      {
        "ticket_id": "DEV-0391",
        "expected_doc_ids": [
          "DOC-SEC-001"
        ],
        "retrieved_doc_ids_top5": [
          "DOC-SEC-001"
        ],
        "top_chunk_ids": [
          "DOC-SEC-001#chunk_0"
        ],
        "top_scores": [
          0.3115
        ],
        "hit": true
      },
      {
        "ticket_id": "DEV-0060",
        "expected_doc_ids": [
          "DOC-DATA-001"
        ],
        "retrieved_doc_ids_top5": [],
        "top_chunk_ids": [],
        "top_scores": [],
        "hit": false
      },
      {
        "ticket_id": "DEV-0429",
        "expected_doc_ids": [
          "DOC-DATA-001"
        ],
        "retrieved_doc_ids_top5": [
          "DOC-DATA-001",
          "DOC-BILL-001",
          "DOC-SEC-001",
          "DOC-SEC-003"
        ],
        "top_chunk_ids": [
          "DOC-DATA-001#chunk_0",
          "DOC-DATA-001#chunk_1",
          "DOC-BILL-001#chunk_0"
        ],
        "top_scores": [
          0.4648,
          0.3176,
          0.3161
        ],
        "hit": true
      },
      {
        "ticket_id": "DEV-0312",
        "expected_doc_ids": [
          "DOC-AUTH-001"
        ],
        "retrieved_doc_ids_top5": [
          "DOC-AUTH-002",
          "DOC-PERF-001",
          "DOC-AUTH-004",
          "DOC-BILL-002"
        ],
        "top_chunk_ids": [
          "DOC-AUTH-002#chunk_1",
          "DOC-AUTH-002#chunk_0",
          "DOC-PERF-001#chunk_0"
        ],
        "top_scores": [
          0.4435,
          0.4326,
          0.4267
        ],
        "hit": false
      },
      {
        "ticket_id": "DEV-0022",
        "expected_doc_ids": [
          "DOC-DATA-001"
        ],
        "retrieved_doc_ids_top5": [
          "DOC-DATA-001",
          "DOC-ONB-001",
          "DOC-DEPLOY-003",
          "DOC-SEC-002"
        ],
        "top_chunk_ids": [
          "DOC-DATA-001#chunk_0",
          "DOC-DATA-001#chunk_1",
          "DOC-ONB-001#chunk_0"
        ],
        "top_scores": [
          0.5814,
          0.5195,
          0.4303
        ],
        "hit": true
      },
      {
        "ticket_id": "DEV-0021",
        "expected_doc_ids": [
          "DOC-SEC-003"
        ],
        "retrieved_doc_ids_top5": [],
        "top_chunk_ids": [],
        "top_scores": [],
        "hit": false
      },
      {
        "ticket_id": "DEV-0065",
        "expected_doc_ids": [
          "DOC-DATA-001"
        ],
        "retrieved_doc_ids_top5": [
          "DOC-DATA-001",
          "DOC-DEPLOY-003",
          "DOC-ONB-001",
          "DOC-SEC-002"
        ],
        "top_chunk_ids": [
          "DOC-DATA-001#chunk_0",
          "DOC-DATA-001#chunk_1",
          "DOC-DEPLOY-003#chunk_1"
        ],
        "top_scores": [
          0.5588,
          0.4973,
          0.4433
        ],
        "hit": true
      },
      {
        "ticket_id": "DEV-0171",
        "expected_doc_ids": [
          "DOC-DEPLOY-001"
        ],
        "retrieved_doc_ids_top5": [
          "DOC-DEPLOY-001",
          "DOC-API-003",
          "DOC-BILL-001",
          "DOC-SEC-001"
        ],
        "top_chunk_ids": [
          "DOC-DEPLOY-001#chunk_0",
          "DOC-API-003#chunk_1",
          "DOC-DEPLOY-001#chunk_2"
        ],
        "top_scores": [
          0.4858,
          0.3892,
          0.3788
        ],
        "hit": true
      },
      {
        "ticket_id": "DEV-0182",
        "expected_doc_ids": [
          "DOC-API-002"
        ],
        "retrieved_doc_ids_top5": [
          "DOC-AUTH-004"
        ],
        "top_chunk_ids": [
          "DOC-AUTH-004#chunk_0"
        ],
        "top_scores": [
          0.3096
        ],
        "hit": false
      },
      {
        "ticket_id": "DEV-0365",
        "expected_doc_ids": [
          "DOC-BILL-003",
          "DOC-API-001"
        ],
        "retrieved_doc_ids_top5": [],
        "top_chunk_ids": [],
        "top_scores": [],
        "hit": false
      },
      {
        "ticket_id": "DEV-0436",
        "expected_doc_ids": [
          "DOC-BILL-003",
          "DOC-API-001"
        ],
        "retrieved_doc_ids_top5": [],
        "top_chunk_ids": [],
        "top_scores": [],
        "hit": false
      },
      {
        "ticket_id": "DEV-0019",
        "expected_doc_ids": [
          "DOC-ACCT-001"
        ],
        "retrieved_doc_ids_top5": [
          "DOC-SEC-001"
        ],
        "top_chunk_ids": [
          "DOC-SEC-001#chunk_0"
        ],
        "top_scores": [
          0.3499
        ],
        "hit": false
      },
      {
        "ticket_id": "DEV-0409",
        "expected_doc_ids": [
          "DOC-AUTH-001"
        ],
        "retrieved_doc_ids_top5": [
          "DOC-AUTH-002",
          "DOC-AUTH-004",
          "DOC-SEC-003",
          "DOC-BILL-001",
          "DOC-BILL-002"
        ],
        "top_chunk_ids": [
          "DOC-AUTH-002#chunk_1",
          "DOC-AUTH-004#chunk_1",
          "DOC-SEC-003#chunk_1"
        ],
        "top_scores": [
          0.5081,
          0.5056,
          0.5005
        ],
        "hit": false
      },
      {
        "ticket_id": "DEV-0155",
        "expected_doc_ids": [
          "DOC-AUTH-003"
        ],
        "retrieved_doc_ids_top5": [],
        "top_chunk_ids": [],
        "top_scores": [],
        "hit": false
      },
      {
        "ticket_id": "DEV-0467",
        "expected_doc_ids": [
          "DOC-API-001"
        ],
        "retrieved_doc_ids_top5": [],
        "top_chunk_ids": [],
        "top_scores": [],
        "hit": false
      },
      {
        "ticket_id": "DEV-0310",
        "expected_doc_ids": [
          "DOC-ONB-001",
          "DOC-ONB-002"
        ],
        "retrieved_doc_ids_top5": [
          "DOC-DEPLOY-003",
          "DOC-SEC-002",
          "DOC-BILL-002",
          "DOC-PERF-002",
          "DOC-SEC-001"
        ],
        "top_chunk_ids": [
          "DOC-DEPLOY-003#chunk_1",
          "DOC-SEC-002#chunk_1",
          "DOC-BILL-002#chunk_0"
        ],
        "top_scores": [
          0.4066,
          0.3891,
          0.379
        ],
        "hit": false
      },
      {
        "ticket_id": "DEV-0172",
        "expected_doc_ids": [
          "DOC-BILL-003",
          "DOC-API-001"
        ],
        "retrieved_doc_ids_top5": [],
        "top_chunk_ids": [],
        "top_scores": [],
        "hit": false
      },
      {
        "ticket_id": "DEV-0326",
        "expected_doc_ids": [
          "DOC-DATA-001"
        ],
        "retrieved_doc_ids_top5": [
          "DOC-DATA-001",
          "DOC-BILL-001",
          "DOC-SEC-001",
          "DOC-AUTH-002"
        ],
        "top_chunk_ids": [
          "DOC-DATA-001#chunk_0",
          "DOC-BILL-001#chunk_0",
          "DOC-SEC-001#chunk_1"
        ],
        "top_scores": [
          0.4208,
          0.3553,
          0.3433
        ],
        "hit": true
      },
      {
        "ticket_id": "DEV-0428",
        "expected_doc_ids": [
          "DOC-ONB-001",
          "DOC-ONB-002"
        ],
        "retrieved_doc_ids_top5": [
          "DOC-ONB-002",
          "DOC-AUTH-004",
          "DOC-SEC-003",
          "DOC-ONB-001"
        ],
        "top_chunk_ids": [
          "DOC-ONB-002#chunk_2",
          "DOC-AUTH-004#chunk_1",
          "DOC-SEC-003#chunk_1"
        ],
        "top_scores": [
          0.4396,
          0.4288,
          0.423
        ],
        "hit": true
      },
      {
        "ticket_id": "DEV-0211",
        "expected_doc_ids": [
          "DOC-SEC-001"
        ],
        "retrieved_doc_ids_top5": [
          "DOC-SEC-001"
        ],
        "top_chunk_ids": [
          "DOC-SEC-001#chunk_0"
        ],
        "top_scores": [
          0.4176
        ],
        "hit": true
      },
      {
        "ticket_id": "DEV-0006",
        "expected_doc_ids": [
          "DOC-DEPLOY-004",
          "DOC-ACCT-002"
        ],
        "retrieved_doc_ids_top5": [
          "DOC-DEPLOY-004",
          "DOC-INT-002",
          "DOC-AUTH-003"
        ],
        "top_chunk_ids": [
          "DOC-DEPLOY-004#chunk_0",
          "DOC-DEPLOY-004#chunk_1",
          "DOC-DEPLOY-004#chunk_2"
        ],
        "top_scores": [
          0.5028,
          0.4082,
          0.3951
        ],
        "hit": true
      }
    ]
  }
}
```