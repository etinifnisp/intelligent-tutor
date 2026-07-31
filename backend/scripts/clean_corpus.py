"""
DEPRECATED — Phase 2 blocks destructive in-place corpus cleaning.

This script previously overwrote raw_text in jee_corpus.json using LLM translation.
Use the Phase 2 pipeline instead:

    python -m pipelines.build_corpus_v2
    python -m pipelines.validate_corpus

Normalization is now stored separately in corpus_v2 text_layers without
overwriting raw extraction.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CORPUS_V1 = PROJECT_ROOT / "data" / "corpus" / "jee_corpus.json"
CORPUS_V2 = PROJECT_ROOT / "data" / "corpus" / "corpus_v2.jsonl"
FROZEN_MANIFEST = PROJECT_ROOT / "data" / "corpus" / "frozen" / "corpus_manifest.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Legacy corpus cleaner (deprecated)")
    parser.add_argument(
        "--force-legacy",
        action="store_true",
        help="DANGEROUS: allow legacy in-place cleaning (not recommended)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("BLOCKED: clean_corpus.py overwrites raw extraction in-place.")
    print("Use: python -m pipelines.build_corpus_v2")
    print("=" * 60)

    if CORPUS_V2.exists():
        print(f"corpus_v2 exists at {CORPUS_V2} — raw text is preserved in text_layers.")
    if FROZEN_MANIFEST.exists():
        print(f"Frozen baseline manifest: {FROZEN_MANIFEST}")

    if not args.force_legacy:
        sys.exit(1)

    print("\n--force-legacy set. Importing legacy cleaner...")
    # Legacy behavior only when explicitly forced
    import clean_corpus as legacy  # type: ignore  # noqa: F401

    legacy.main()


if __name__ == "__main__":
    main()
