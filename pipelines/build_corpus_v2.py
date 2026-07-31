"""
Build corpus_v2.jsonl from legacy jee_corpus.json with traceable transformations.

Usage:
    python -m pipelines.build_corpus_v2
    python -m pipelines.build_corpus_v2 --force
    python -m pipelines.build_corpus_v2 --paper JEE_Main_2025_Apr02_Shift1.pdf
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipelines.confidence import (
    assign_review_status,
    needs_review_queue,
    score_answer_key,
    score_classification,
    score_extraction,
)
from pipelines.config import (
    CORPUS_V1_PATH,
    CORPUS_V2_PATH,
    DATA_DIR,
    DIAGRAM_INDEX_PATH,
    EXTRACTION_ERRORS_PATH,
    IMAGES_DIR,
    PAPER_REGISTRY_PATH,
    PAPERS_DIR,
    PIPELINE_VERSION,
    REVIEW_QUEUE_PATH,
    SCHEMA_VERSION,
)
from pipelines.duplicates import assign_duplicate_groups
from pipelines.identifiers import (
    normalize_difficulty,
    normalize_exam_type,
    paper_id_from_filename,
    question_id_from_parts,
)
from pipelines.paper_registry import (
    load_registry,
    mark_paper_processed,
    paper_needs_reprocess,
    save_registry,
)
from pipelines.pdf_enricher import enrich_from_pdf, find_pdf_for_paper, link_legacy_images, sha256_file
from pipelines.question_parser import extract_question_number_in_paper, parse_raw_text
from pipelines.text_normalize import build_text_layers


def load_v1_corpus(path: Path) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_existing_v2(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    records: dict[str, dict[str, Any]] = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            records[row["question_id"]] = row
    return records


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def transform_question(
    q: dict[str, Any],
    *,
    enrich_pdf: bool = True,
    pdf_cache: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    raw_text = q.get("raw_text", "") or ""
    layers = build_text_layers(raw_text)
    parsed = parse_raw_text(layers["normalized_text"], q.get("question_type", "MCQ-single"))
    qnum_in_paper = extract_question_number_in_paper(raw_text)

    paper_filename = q.get("paper_filename", "")
    legacy_number = q.get("question_number")
    paper_id = paper_id_from_filename(paper_filename)
    question_id = question_id_from_parts(paper_filename, legacy_number)

    pdf_meta: dict[str, Any] = {
        "source_pdf_hash": None,
        "source_pdf_path": None,
        "page_number": None,
        "question_bbox": None,
        "diagram_paths": [],
        "diagrams": [],
        "pdf_enrichment_status": "skipped",
    }
    if enrich_pdf:
        pdf_path = find_pdf_for_paper(PAPERS_DIR, paper_filename)
        if pdf_path:
            pdf_meta = enrich_from_pdf(
                pdf_path,
                parsed.stem_text or layers["normalized_text"][:200],
                paper_id,
                question_id,
                IMAGES_DIR,
            )
        else:
            pdf_meta["pdf_enrichment_status"] = "pdf_not_found"

    legacy_diagrams = link_legacy_images(IMAGES_DIR, paper_filename, legacy_number)
    if legacy_diagrams and not pdf_meta.get("diagram_paths"):
        pdf_meta["diagram_paths"] = legacy_diagrams
        pdf_meta["diagrams"] = [
            {
                "diagram_id": f"{question_id}_legacy_{i+1}",
                "path": p,
                "page_number": None,
                "bbox": None,
                "source": "legacy_image_store",
            }
            for i, p in enumerate(legacy_diagrams)
        ]

    has_pdf_match = pdf_meta.get("pdf_enrichment_status") == "matched"
    has_diagrams = bool(pdf_meta.get("diagram_paths"))
    extraction_confidence = score_extraction(parsed, has_pdf_match, has_diagrams)
    classification_confidence = score_classification(
        q.get("chapter", ""), q.get("topic", ""), q.get("subject", "")
    )
    answer_key_confidence = score_answer_key(parsed)

    extraction_errors = [
        {"code": err, "message": err.replace("_", " ")}
        for err in parsed.parse_errors
    ]
    if pdf_meta.get("pdf_enrichment_status") not in {
        "matched",
        "skipped",
        "pdf_not_found",
        "stem_too_short",
    }:
        extraction_errors.append(
            {
                "code": "pdf_enrichment_issue",
                "message": pdf_meta.get("pdf_enrichment_status", "unknown"),
            }
        )

    review_status = assign_review_status(
        extraction_confidence,
        answer_key_confidence,
        parsed.parse_errors,
        is_duplicate=False,
    )

    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "question_id": question_id,
        "paper_id": paper_id,
        "paper_filename": paper_filename,
        "exam_type": normalize_exam_type(q.get("exam_type", "")),
        "year": q.get("year"),
        "session": q.get("session"),
        "shift": q.get("shift"),
        "subject": q.get("subject"),
        "chapter": q.get("chapter"),
        "topic": q.get("topic"),
        "legacy_question_number": legacy_number,
        "question_number_in_paper": qnum_in_paper,
        "question_type": parsed.question_type,
        "stem_text": parsed.stem_text,
        "stem_latex": None,
        "options": parsed.options,
        "correct_answer": parsed.correct_answer,
        "official_solution": parsed.official_solution,
        "text_layers": layers,
        "raw_text": raw_text,
        "normalized_text": layers["normalized_text"],
        "page_number": pdf_meta.get("page_number"),
        "question_bbox": pdf_meta.get("question_bbox"),
        "diagram_paths": pdf_meta.get("diagram_paths", []),
        "diagram_ids": [d["diagram_id"] for d in pdf_meta.get("diagrams", [])],
        "source_pdf_hash": pdf_meta.get("source_pdf_hash"),
        "source_pdf_path": pdf_meta.get("source_pdf_path"),
        "pdf_enrichment_status": pdf_meta.get("pdf_enrichment_status"),
        "concept_ids": [],
        "prerequisite_ids": [],
        "difficulty": normalize_difficulty(q.get("difficulty", "")),
        "marks_positive": q.get("marks_positive"),
        "marks_negative": q.get("marks_negative"),
        "extraction_confidence": extraction_confidence,
        "classification_confidence": classification_confidence,
        "answer_key_confidence": answer_key_confidence,
        "answer_key_source": "embedded_in_text" if parsed.correct_answer else None,
        "review_status": review_status,
        "duplicate_of": None,
        "duplicate_group_id": None,
        "extraction_errors": extraction_errors,
        "pipeline_version": PIPELINE_VERSION,
        "built_at": datetime.now(timezone.utc).isoformat(),
    }

    diagram_rows = pdf_meta.get("diagrams", [])
    error_rows = [
        {
            "question_id": question_id,
            "paper_filename": paper_filename,
            "legacy_question_number": legacy_number,
            **err,
        }
        for err in extraction_errors
    ]
    return record, diagram_rows, error_rows


def load_jsonl_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_corpus_v2(
    *,
    force: bool = False,
    paper_filter: str | None = None,
    skip_pdf: bool = False,
) -> dict[str, Any]:
    if not CORPUS_V1_PATH.exists():
        raise FileNotFoundError(f"V1 corpus not found: {CORPUS_V1_PATH}")

    v1 = load_v1_corpus(CORPUS_V1_PATH)
    registry = load_registry(PAPER_REGISTRY_PATH)
    existing_v2 = load_existing_v2(CORPUS_V2_PATH)

    full_rebuild = force and not paper_filter
    by_id: dict[str, dict[str, Any]] = {} if full_rebuild else dict(existing_v2)
    all_diagrams: list[dict[str, Any]] = [] if full_rebuild else load_jsonl_list(DIAGRAM_INDEX_PATH)
    all_errors: list[dict[str, Any]] = [] if full_rebuild else load_jsonl_list(EXTRACTION_ERRORS_PATH)

    by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for q in v1:
        by_paper[q.get("paper_filename", "")].append(q)

    papers_processed = 0
    papers_skipped = 0

    for paper_filename, questions in sorted(by_paper.items()):
        if paper_filter and paper_filename != paper_filter:
            continue

        needs, paper_info = paper_needs_reprocess(
            registry, paper_filename, PAPERS_DIR, force=force
        )
        if not needs and not full_rebuild:
            papers_skipped += 1
            continue

        replaced_ids: set[str] = set()
        for q in questions:
            record, diagrams, errors = transform_question(
                q, enrich_pdf=not skip_pdf, pdf_cache=None
            )
            qid = record["question_id"]
            replaced_ids.add(qid)
            by_id[qid] = record
            for d in diagrams:
                d["question_id"] = qid
                d["paper_id"] = record["paper_id"]
            all_diagrams = [d for d in all_diagrams if d.get("question_id") != qid]
            all_diagrams.extend(diagrams)
            all_errors = [e for e in all_errors if e.get("question_id") != qid]
            all_errors.extend(errors)

        mark_paper_processed(
            registry,
            paper_filename,
            paper_info.get("pdf_hash"),
            len(questions),
        )
        papers_processed += 1

    all_records = list(by_id.values())
    all_records = assign_duplicate_groups(all_records)

    review_queue = [q for q in all_records if needs_review_queue(q)]

    write_jsonl(CORPUS_V2_PATH, all_records)
    write_jsonl(DIAGRAM_INDEX_PATH, all_diagrams)
    write_jsonl(EXTRACTION_ERRORS_PATH, all_errors)
    write_jsonl(REVIEW_QUEUE_PATH, review_queue)
    save_registry(PAPER_REGISTRY_PATH, registry)

    return {
        "question_count": len(all_records),
        "diagram_count": len(all_diagrams),
        "error_count": len(all_errors),
        "review_queue_count": len(review_queue),
        "papers_processed": papers_processed,
        "papers_skipped": papers_skipped,
        "corpus_v2_path": str(CORPUS_V2_PATH),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build trustworthy corpus_v2.jsonl")
    parser.add_argument("--force", action="store_true", help="Reprocess all papers")
    parser.add_argument("--paper", help="Process only one paper filename")
    parser.add_argument("--skip-pdf", action="store_true", help="Skip PDF enrichment")
    args = parser.parse_args()

    summary = build_corpus_v2(
        force=args.force,
        paper_filter=args.paper,
        skip_pdf=args.skip_pdf,
    )
    print("Corpus v2 build complete:")
    for key, value in summary.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
