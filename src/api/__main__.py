"""Run API server: python -m src.api"""

from __future__ import annotations

import os


def main() -> None:
    try:
        import uvicorn
    except Exception as e:
        raise SystemExit(
            "uvicorn is required to run the API server (pip install uvicorn). "
            f"Import error: {e}"
        )
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "false").lower() in {"1", "true", "yes"}
    uvicorn.run("src.api.app:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
