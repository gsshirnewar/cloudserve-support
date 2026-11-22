"""Ticket ingest and normalization (T16).

Normalizes tickets from all supported channels into a single internal model,
preserves raw text/channel, and tolerates malformed inputs without crashing.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from src.logging_config import get_logger
from src.schemas import Channel, NormalisedTicket

logger = get_logger(__name__)

SUPPORTED_CHANNELS = {"email", "chat", "docs_comment", "forum"}


def _as_str_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return str(value)
    except Exception:
        return None


def _as_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        # Handle common ISO-8601 forms including trailing Z.
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None
    return None


def _build_raw_text(subject: Optional[str], body: Optional[str]) -> str:
    parts: List[str] = []
    if subject is not None and subject != "":
        parts.append(subject)
    if body is not None and body != "":
        parts.append(body)
    return "\n\n".join(parts) if parts else (body or "")


def _stable_fallback_ticket_id(original: Any, index: Optional[int] = None) -> str:
    try:
        payload = json.dumps(original, sort_keys=True, ensure_ascii=False, default=str)
    except Exception:
        payload = repr(original)
    digest = hashlib.sha1(payload.encode("utf-8", errors="replace")).hexdigest()[:12]
    if index is None:
        return f"UNKNOWN-{digest}"
    return f"UNKNOWN-{index}-{digest}"


def normalize_ticket(raw_ticket: Any, index: Optional[int] = None) -> NormalisedTicket:
    """Normalize a single raw ticket into NormalisedTicket.

    Never raises: malformed inputs produce a flagged normalized record.
    """
    warnings: List[str] = []
    try:
        if isinstance(raw_ticket, Mapping):
            original: Dict[str, Any] = dict(raw_ticket)
        elif raw_ticket is None:
            original = {}
            warnings.append("input_ticket_is_null")
        else:
            # Wrong top-level type: preserve representation and flag.
            original = {"__raw_value__": raw_ticket}
            warnings.append(f"input_not_mapping:{type(raw_ticket).__name__}")

        raw_id = original.get("ticket_id")
        ticket_id = _as_str_or_none(raw_id)
        if ticket_id is None or ticket_id.strip() == "":
            ticket_id = _stable_fallback_ticket_id(original, index=index)
            warnings.append("missing_or_invalid_ticket_id")

        raw_channel = original.get("channel")
        channel_str = (_as_str_or_none(raw_channel) or "").strip().lower()
        if channel_str in SUPPORTED_CHANNELS:
            channel = Channel(channel_str)
        elif channel_str == "":
            channel = Channel.UNKNOWN
            warnings.append("missing_channel")
        else:
            channel = Channel.UNKNOWN
            warnings.append(f"unsupported_channel:{channel_str}")

        subject = _as_str_or_none(original.get("subject"))
        body = _as_str_or_none(original.get("body"))
        if original.get("subject") is not None and not isinstance(original.get("subject"), str):
            warnings.append("coerced_subject_to_string")
        if original.get("body") is not None and not isinstance(original.get("body"), str):
            warnings.append("coerced_body_to_string")
        if body is None:
            body = ""
            if "body" not in original:
                warnings.append("missing_body")
            else:
                warnings.append("null_body_coerced_to_empty")
        if subject is None and "subject" in original and original.get("subject") is None:
            # Preserve None vs empty distinction only informationally; normalized field remains None.
            warnings.append("null_subject")

        received_at = _parse_datetime(original.get("received_at"))
        if original.get("received_at") is not None and received_at is None:
            warnings.append("invalid_received_at")

        labels = _as_dict(original.get("labels"))
        history = _as_dict(original.get("history"))
        if original.get("labels") is not None and not isinstance(original.get("labels"), dict):
            warnings.append("invalid_labels_type")
        if original.get("history") is not None and not isinstance(original.get("history"), dict):
            warnings.append("invalid_history_type")

        customer: Dict[str, Any] = {}
        if isinstance(original.get("customer"), dict):
            customer.update(original.get("customer", {}))
        # Promote common flat fields when present (dev dataset shape).
        for key in (
            "customer_id",
            "customer_name",
            "customer_tier",
            "customer_region",
            "language_fluency",
        ):
            if key in original and key not in customer:
                customer[key] = original.get(key)

        raw_text = _build_raw_text(subject, body)
        metadata: Dict[str, Any] = {
            "normalized_from_index": index,
            "source_channel_raw": raw_channel,
        }

        normalized = NormalisedTicket(
            ticket_id=ticket_id,
            channel=channel,
            subject=subject,
            body=body,
            raw_text=raw_text,
            received_at=received_at,
            customer=customer,
            labels=labels,
            history=history,
            metadata=metadata,
            ingest_warnings=warnings,
            original=original,
        )
        return normalized
    except Exception as e:
        # Absolute safety: never raise, return flagged minimal record.
        fallback_id = _stable_fallback_ticket_id(raw_ticket, index=index)
        logger.exception(
            "Failed to normalize ticket; returning flagged record",
            extra={"component": "ingest", "event": "normalize_error", "ticket_id": fallback_id},
        )
        original: Dict[str, Any]
        if isinstance(raw_ticket, Mapping):
            original = dict(raw_ticket)
        else:
            original = {"__raw_value__": repr(raw_ticket)}
        return NormalisedTicket(
            ticket_id=fallback_id,
            channel=Channel.UNKNOWN,
            subject=None,
            body="",
            raw_text="",
            received_at=None,
            customer={},
            labels={},
            history={},
            metadata={"normalized_from_index": index, "normalization_failed": True},
            ingest_warnings=["normalization_exception", f"error:{type(e).__name__}"],
            original=original,
        )


def ingest_tickets(raw_tickets: Sequence[Any]) -> Tuple[List[NormalisedTicket], Dict[str, Any]]:
    """Normalize a batch of tickets, collecting flagged records instead of failing."""
    normalized: List[NormalisedTicket] = []
    flagged = 0
    for idx, raw in enumerate(raw_tickets):
        record = normalize_ticket(raw, index=idx)
        normalized.append(record)
        if record.ingest_warnings or record.metadata.get("normalization_failed"):
            flagged += 1
    stats = {
        "input_count": len(raw_tickets),
        "output_count": len(normalized),
        "flagged_count": flagged,
        "failed_count": sum(1 for r in normalized if r.metadata.get("normalization_failed")),
    }
    return normalized, stats
