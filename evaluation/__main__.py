"""Module entrypoint for `python -m evaluation` and `python -m evaluation.harness` support."""

from evaluation.harness import main


if __name__ == "__main__":
    raise SystemExit(main())
