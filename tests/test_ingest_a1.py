import json
from pathlib import Path

from src.ingest import ingest_tickets, normalize_ticket


def _load_dev():
    root = Path(__file__).resolve().parents[1]
    with (root / "data" / "development_tickets.json").open("r", encoding="utf-8") as f:
        return json.load(f)


def _sample_by_channel(tickets, channel):
    return next(t for t in tickets if t.get("channel") == channel)


def test_ingest_normalizes_email_ticket():
    tickets = _load_dev()
    norm = normalize_ticket(_sample_by_channel(tickets, "email"))
    assert norm.channel.value == "email"
    assert norm.ticket_id
    assert norm.original.get("ticket_id") == norm.ticket_id


def test_ingest_normalizes_chat_ticket():
    tickets = _load_dev()
    norm = normalize_ticket(_sample_by_channel(tickets, "chat"))
    assert norm.channel.value == "chat"
    assert norm.ticket_id
    assert isinstance(norm.body, str)


def test_ingest_normalizes_docs_comment_ticket():
    tickets = _load_dev()
    norm = normalize_ticket(_sample_by_channel(tickets, "docs_comment"))
    assert norm.channel.value == "docs_comment"
    assert norm.ticket_id


def test_ingest_normalizes_forum_ticket():
    tickets = _load_dev()
    norm = normalize_ticket(_sample_by_channel(tickets, "forum"))
    assert norm.channel.value == "forum"
    assert norm.ticket_id


def test_ingest_preserves_raw_text_and_channel():
    tickets = _load_dev()
    for ch in ["email", "chat", "docs_comment", "forum"]:
        raw = _sample_by_channel(tickets, ch)
        norm = normalize_ticket(raw)
        assert norm.channel.value == ch
        assert norm.original.get("body") == raw.get("body")
        assert norm.original.get("subject") == raw.get("subject")
        # raw_text should reflect available text (may be body-only for empty subject)
        if raw.get("body"):
            assert raw.get("body") in norm.raw_text


def test_ingest_handles_missing_fields_and_empty_body():
    norm = normalize_ticket({"channel": "chat"}, index=0)
    assert norm.ticket_id  # fallback generated
    assert norm.channel.value == "chat"
    assert norm.body == ""
    assert norm.ingest_warnings  # flagged, not failed
    assert norm.metadata.get("normalization_failed") is not True


def test_ingest_handles_unicode_and_long_body():
    long_body = ("Hello 🌍 שלום مرحبا " * 4000)[:50000]
    raw = {
        "ticket_id": "UNI-1",
        "channel": "email",
        "subject": "Unicode ✓",
        "body": long_body,
        "received_at": "2026-01-01T00:00:00Z",
    }
    norm = normalize_ticket(raw)
    assert norm.ticket_id == "UNI-1"
    assert "🌍" in norm.body
    assert "שלום" in norm.body
    assert len(norm.body) == 50000
    assert norm.metadata.get("normalization_failed") is not True


def test_ingest_handles_wrong_types_without_exception():
    raw = {
        "ticket_id": 12345,
        "channel": "forum",
        "subject": ["not", "a", "string"],
        "body": {"nested": "object"},
        "labels": "bad",
        "history": 7,
        "received_at": 123,
    }
    norm = normalize_ticket(raw)
    assert norm.ticket_id == "12345"
    assert norm.channel.value == "forum"
    assert isinstance(norm.subject, str)
    assert isinstance(norm.body, str)
    assert norm.ingest_warnings
    assert norm.metadata.get("normalization_failed") is not True


def test_ingest_batch_500_dev_tickets_zero_failures():
    tickets = _load_dev()
    normalized, stats = ingest_tickets(tickets)
    assert stats["input_count"] == 500
    assert stats["output_count"] == 500
    assert stats["failed_count"] == 0
    # every output must have stable ticket_id and parseable shape
    assert all(n.ticket_id for n in normalized)
    assert all(n.channel is not None for n in normalized)
