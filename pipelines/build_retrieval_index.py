"""Build hybrid retrieval indexes from corpus_v2.

Usage:
    python -m pipelines.build_retrieval_index
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from app.retrieval.indexer import build_indexes  # noqa: E402


def main() -> None:
    manifest = build_indexes()
    print("Retrieval index build complete:")
    for k, v in manifest.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
