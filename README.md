# CloudServe Support System (Capstone)

CloudServe support-system capstone implementation.

## Prerequisites
- Python **3.10+** (developed/test target per brief; verify locally)
- Access to **OpenRouter** or **Groq** free-tier API key

## Setup (clean checkout)
```powershell
# from repository root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and set OPENROUTER_API_KEY or GROQ_API_KEY
```

## Task T01 smoke test
```powershell
python scripts/smoke_test.py
```
Expected output includes:
- `[model] reply=...` (real provider response)
- `[embeddings] dimension=384` (for `all-MiniLM-L6-v2`)
- `[chroma] query_ids=...` showing the inserted smoke-test document
- `== SMOKE TEST PASSED ==`

## Notes
- Do **not** commit `.env` or real credentials. `.env.example` contains placeholders only.
- `storage/` and `evaluation/results/` contents are ignored by git except `.gitkeep` files.
- Pinned dependencies are based on the capstone configuration template; adjust pins if your local Python version requires compatibility updates, and record any change in `ATTRIBUTION.md` / docs.

## Run an evaluation (T24)

Use the development tickets for gate rehearsal and iteration. Keep the validation dataset for its single recorded final run after evaluation and threshold decisions are frozen.

```powershell
# From cloudserve-support/
python -m evaluation.harness --input data\development_tickets.json --output evaluation\results\dev-run
```

The harness accepts a JSON array, `{"tickets": [...]}`, one ticket object, or JSONL. It processes all selected tickets, isolates individual ticket failures, and writes:

- `results.jsonl` — one output per input index, including the pipeline trace and non-PII metric observations.
- `metrics.json` and `metrics.md` — volume, business, classification, retrieval, latency, calibration, governance, and group-slice metrics.
- `run_manifest.json` — input fingerprint, run id, status, and checkpoint progress.
- `decision_log.db` — run-scoped SQLite audit records used for reconciliation.

If execution is interrupted, rerun the same input and options with `--resume` and the same output directory. The harness verifies the input fingerprint and recovers decisions already committed to SQLite before the result checkpoint was written. Use a new output directory for a fresh run. Optional flags: `--workers N` sets bounded ticket concurrency; `--max-tickets N` limits a local smoke run.

## Project layout
See the capstone project plan for the target structure under `src/`, `evaluation/`, `prompts/`, `docs/`, `tests/`, `ui/`, and `ops/`.
