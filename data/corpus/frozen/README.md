# Frozen Corpus (Phase 1 Baseline)

This directory holds an immutable snapshot of the question corpus taken before
architecture migration.

| File | Purpose |
|------|---------|
| `corpus_manifest.json` | SHA-256 hash, timestamp, question count |
| `jee_corpus_v1_baseline.json` | Byte-for-byte copy of `../jee_corpus.json` at freeze time |

Regenerate with:

```bash
python backend/scripts/collect_baseline.py
```

Do not edit the frozen JSON manually. Future corpus changes go through the
Phase 2 pipeline and produce `corpus_v2.jsonl`.
