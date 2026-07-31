"""PDF hashing, text search, bounding boxes, and diagram extraction."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Optional

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    fitz = None  # type: ignore


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_pdf_for_paper(papers_dir: Path, paper_filename: str) -> Optional[Path]:
    if not paper_filename:
        return None
    candidates = [
        papers_dir / "mains" / paper_filename,
        papers_dir / "advanced" / paper_filename,
        papers_dir / paper_filename,
    ]
    for path in candidates:
        if path.exists():
            return path
    # Case-insensitive fallback
    name_lower = paper_filename.lower()
    for sub in ("mains", "advanced", ""):
        base = papers_dir / sub if sub else papers_dir
        if not base.exists():
            continue
        for path in base.rglob("*.pdf"):
            if path.name.lower() == name_lower:
                return path
    return None


def _search_snippet(page: "fitz.Page", snippet: str) -> Optional[tuple[int, list[float]]]:
    words = snippet.split()
    if len(words) < 4:
        probe = snippet[:80].strip()
    else:
        probe = " ".join(words[:8])
    if len(probe) < 12:
        return None
    rects = page.search_for(probe[:60])
    if not rects:
        rects = page.search_for(probe[:40])
    if not rects:
        return None
    rect = rects[0]
    return page.number + 1, [rect.x0, rect.y0, rect.x1, rect.y1]


def extract_diagrams_from_page(
    doc: "fitz.Document",
    page_number: int,
    question_bbox: Optional[list[float]],
    output_dir: Path,
    paper_id: str,
    question_id: str,
) -> list[dict[str, Any]]:
    if fitz is None:
        return []
    page = doc[page_number - 1]
    output_dir.mkdir(parents=True, exist_ok=True)
    diagrams: list[dict[str, Any]] = []

    bbox_rect = None
    if question_bbox and len(question_bbox) == 4:
        bbox_rect = fitz.Rect(*question_bbox)

    for img_index, img in enumerate(page.get_images(full=True)):
        xref = img[0]
        try:
            img_rects = page.get_image_rects(xref)
        except Exception:
            continue
        for rect_index, rect in enumerate(img_rects):
            if bbox_rect and not bbox_rect.intersects(rect):
                continue
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.n >= 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                filename = f"{paper_id}_{question_id}_p{page_number}_img{img_index}_{rect_index}.png"
                out_path = output_dir / filename
                pix.save(str(out_path))
                rel_path = str(out_path.relative_to(output_dir.parent.parent))
                diagrams.append(
                    {
                        "diagram_id": f"{question_id}_d{len(diagrams)+1}",
                        "path": rel_path.replace("\\", "/"),
                        "page_number": page_number,
                        "bbox": [rect.x0, rect.y0, rect.x1, rect.y1],
                        "source": "pdf_image_xref",
                    }
                )
            except Exception:
                continue
    return diagrams


def enrich_from_pdf(
    pdf_path: Path,
    stem_text: str,
    paper_id: str,
    question_id: str,
    images_output_dir: Path,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "source_pdf_hash": sha256_file(pdf_path),
        "source_pdf_path": str(pdf_path),
        "page_number": None,
        "question_bbox": None,
        "diagram_paths": [],
        "diagrams": [],
        "pdf_enrichment_status": "not_attempted",
    }
    if fitz is None:
        result["pdf_enrichment_status"] = "pymupdf_unavailable"
        return result

    snippet = re.sub(r"\s+", " ", stem_text)[:120].strip()
    if len(snippet) < 15:
        result["pdf_enrichment_status"] = "stem_too_short"
        return result

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as exc:
        result["pdf_enrichment_status"] = f"open_failed:{exc}"
        return result

    try:
        for page in doc:
            hit = _search_snippet(page, snippet)
            if hit:
                page_number, bbox = hit
                result["page_number"] = page_number
                result["question_bbox"] = bbox
                diagrams = extract_diagrams_from_page(
                    doc,
                    page_number,
                    bbox,
                    images_output_dir / paper_id,
                    paper_id,
                    question_id,
                )
                result["diagrams"] = diagrams
                result["diagram_paths"] = [d["path"] for d in diagrams]
                result["pdf_enrichment_status"] = "matched"
                break
        else:
            result["pdf_enrichment_status"] = "no_page_match"
    finally:
        doc.close()

    return result


def link_legacy_images(
    images_dir: Path,
    paper_filename: str,
    legacy_question_number: int,
) -> list[str]:
    if not paper_filename or legacy_question_number is None:
        return []
    paper_basename = paper_filename.replace(".pdf", "")
    q_dir = images_dir / paper_basename
    if not q_dir.exists():
        return []
    prefix = f"img_{legacy_question_number}_"
    paths = []
    for img in sorted(q_dir.iterdir()):
        if img.name.startswith(prefix) and img.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            paths.append(f"images/{paper_basename}/{img.name}")
    return paths
