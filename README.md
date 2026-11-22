# CloudServe Support System (Capstone)

Working project scaffold for the Forward Deployed AI Engineering capstone (Task T01 completed).

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

## Project layout
See the capstone project plan for the target structure under `src/`, `evaluation/`, `prompts/`, `docs/`, `tests/`, `ui/`, and `ops/`.
