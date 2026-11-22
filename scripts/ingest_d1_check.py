"""D1 checkpoint: print normalized ticket for one sample per channel."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingest import normalize_ticket

CHANNELS = ["email", "chat", "docs_comment", "forum"]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    data_path = root / "data" / "development_tickets.json"
    tickets = json.loads(data_path.read_text(encoding="utf-8"))

    shapes = []
    for ch in CHANNELS:
        raw = next(t for t in tickets if t.get("channel") == ch)
        norm = normalize_ticket(raw)
        obj = norm.model_dump(mode="json")
        print(f"\n=== {ch} ({norm.ticket_id}) ===")
        print(json.dumps(obj, ensure_ascii=False, indent=2))
        shapes.append((ch, list(obj.keys())))

    print("\n=== SHAPE CHECK ===")
    base = shapes[0][1]
    for ch, keys in shapes:
        print(ch, "identical_shape=", keys == base, "keys=", keys)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
