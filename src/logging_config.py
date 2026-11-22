"""Structured logging configuration for the application."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class JsonFormatter(logging.Formatter):
    """Minimal JSON log formatter for structured logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # Include selected extra fields when present.
        for key in ("ticket_id", "component", "event", "run_id", "outcome", "latency_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO", log_format: str = "json") -> None:
    """Configure root logging once with JSON or text output."""
    root = logging.getLogger()
    normalized_level = getattr(logging, (level or "INFO").upper(), logging.INFO)
    root.setLevel(normalized_level)

    # Avoid duplicate handlers on repeated calls (tests/harness).
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        if (log_format or "json").lower() == "json":
            handler.setFormatter(JsonFormatter())
        else:
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
            )
        root.addHandler(handler)
    else:
        for handler in root.handlers:
            if (log_format or "json").lower() == "json":
                handler.setFormatter(JsonFormatter())

    # Keep third-party libraries quieter by default unless DEBUG requested.
    if normalized_level > logging.DEBUG:
        for noisy in ("httpx", "chromadb", "urllib3", "openai"):
            logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a module/component logger."""
    return logging.getLogger(name or "cloudserve")
