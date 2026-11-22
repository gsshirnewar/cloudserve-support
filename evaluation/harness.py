"""Evaluation harness CLI stub (T14).

T24 will implement unattended processing and metrics reporting. This skeleton
provides the documented command and required arguments.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Sequence

from src.config import get_config
from src.logging_config import configure_logging, get_logger


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m evaluation.harness",
        description="Run the CloudServe evaluation harness on a ticket dataset.",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to input ticket dataset (e.g. JSON file matching ticket schema).",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Directory path where run outputs/metrics will be written.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpointed progress if supported (stub/no-op in T14).",
    )
    parser.add_argument(
        "--max-tickets",
        type=int,
        default=None,
        help="Optional limit for local smoke runs (stub/no-op in T14).",
    )
    return parser


def run_harness(input_path: str, output_path: str, resume: bool = False, max_tickets: Optional[int] = None) -> int:
    """Stub harness entrypoint. Returns process exit code."""
    config = get_config()
    configure_logging(level=config.runtime.log_level, log_format=config.runtime.log_format)
    logger = get_logger("evaluation.harness")

    in_path = Path(input_path)
    out_dir = Path(output_path)
    logger.info(
        "Harness stub invoked (implementation pending T24)",
        extra={
            "event": "harness_stub",
            "component": "evaluation.harness",
            "outcome": "not_implemented",
        },
    )
    print(f"[harness:stub] input={in_path} output={out_dir} resume={resume} max_tickets={max_tickets}")
    print("Evaluation harness is a stub in T14. Full unattended processing will be implemented in T24.")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    return run_harness(
        input_path=args.input,
        output_path=args.output,
        resume=args.resume,
        max_tickets=args.max_tickets,
    )


if __name__ == "__main__":
    raise SystemExit(main())
