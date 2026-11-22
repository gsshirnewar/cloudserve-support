"""Task T01 smoke test.

Verifies:
1. Model provider connectivity (OpenRouter or Groq) and prints a model reply.
2. Embedding model loads and prints vector dimension (expected 384 for all-MiniLM-L6-v2).
3. Chroma add/query round-trip works at CHROMA_PATH.

Run from project root:
    python scripts/smoke_test.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_env() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("python-dotenv is required. Install dependencies from requirements.txt.") from exc

    root = project_root()
    load_dotenv(root / ".env")
    load_dotenv(root / ".env.local", override=False)


def get_provider_config() -> tuple[str, str, str, str]:
    """Return (provider, api_key, base_url, model)."""
    provider = (os.getenv("LLM_PROVIDER") or "openrouter").strip().lower()
    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").strip()
        model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip()
        return provider, api_key, base_url, model

    provider = "openrouter"
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
    model = os.getenv("OPENROUTER_MODEL") or os.getenv("MODEL_NAME") or "meta-llama/llama-3.1-8b-instruct"
    return provider, api_key, base_url, model.strip()


def test_model_reply() -> None:
    provider, api_key, base_url, model = get_provider_config()
    placeholder_values = {"", "your_key_here", "your_openrouter_key_here", "your_groq_key_here"}
    if api_key in placeholder_values:
        raise RuntimeError(
            f"No valid API key configured for provider '{provider}'. "
            "Set OPENROUTER_API_KEY or GROQ_API_KEY in .env (see .env.example)."
        )

    try:
        from openai import OpenAI  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("openai package is required. Install dependencies from requirements.txt.") from exc

    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Reply with exactly: SMOKE_TEST_OK"},
        ],
        temperature=0,
        max_tokens=20,
    )
    reply = (response.choices[0].message.content or "").strip()
    print(f"[model] provider={provider} model={model}")
    print(f"[model] reply={reply}")


def test_embeddings() -> int:
    model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2").strip() or "all-MiniLM-L6-v2"
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("sentence-transformers is required. Install dependencies from requirements.txt.") from exc

    model = SentenceTransformer(model_name)
    vector = model.encode("CloudServe smoke test embedding.")
    dim = len(vector)
    print(f"[embeddings] model={model_name}")
    print(f"[embeddings] dimension={dim}")
    return dim


def test_chroma_round_trip() -> None:
    chroma_path = os.getenv("CHROMA_PATH", "./storage/chroma").strip() or "./storage/chroma"
    path = (project_root() / chroma_path).resolve() if not os.path.isabs(chroma_path) else Path(chroma_path)
    path.mkdir(parents=True, exist_ok=True)

    try:
        import chromadb  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("chromadb is required. Install dependencies from requirements.txt.") from exc

    client = chromadb.PersistentClient(path=str(path))
    collection = client.get_or_create_collection(name="smoke_test")
    doc_id = "smoke-1"
    # Reset prior smoke doc if present
    try:
        collection.delete(ids=[doc_id])
    except Exception:
        pass
    collection.add(
        ids=[doc_id],
        documents=["CloudServe support smoke test document."],
        metadatas=[{"source": "smoke_test"}],
    )
    results = collection.query(query_texts=["CloudServe smoke test"], n_results=1)
    ids = (results.get("ids") or [[]])[0]
    docs = (results.get("documents") or [[]])[0]
    print(f"[chroma] path={path}")
    print(f"[chroma] query_ids={ids}")
    print(f"[chroma] query_doc={docs[0] if docs else ''}")
    if doc_id not in ids:
        raise RuntimeError("Chroma round-trip failed: inserted document not returned by query.")


def main() -> int:
    os.chdir(project_root())
    load_env()

    print("== CloudServe T01 Smoke Test ==")
    test_model_reply()
    dim = test_embeddings()
    test_chroma_round_trip()

    if dim != 384:
        print(f"[warn] Expected embedding dimension 384 for all-MiniLM-L6-v2, got {dim}.")
    print("== SMOKE TEST PASSED ==")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"== SMOKE TEST FAILED: {exc} ==", file=sys.stderr)
        raise SystemExit(1)
