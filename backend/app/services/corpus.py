import json
import logging
import os
from pathlib import Path
from typing import List

from app.config import CORPUS_PATH, IMAGES_DIR

logger = logging.getLogger("tutor.boot")

QUESTIONS_RAM: List[dict] = []


def load_questions_into_ram() -> None:
    global QUESTIONS_RAM
    logger.info("Loading question corpus from '%s'...", CORPUS_PATH)

    if not CORPUS_PATH.exists():
        logger.warning("Question bank file '%s' not found on disk.", CORPUS_PATH)
        QUESTIONS_RAM = []
        return

    try:
        with open(CORPUS_PATH, "r", encoding="utf-8") as f:
            QUESTIONS_RAM = json.load(f)

        if IMAGES_DIR.exists():
            for q in QUESTIONS_RAM:
                q["images"] = []
                paper_filename = q.get("paper_filename", "")
                q_num = q.get("question_number")
                if not paper_filename or q_num is None:
                    continue

                paper_basename = paper_filename.replace(".pdf", "")
                q_dir = IMAGES_DIR / paper_basename
                if not q_dir.exists():
                    continue

                prefix = f"img_{q_num}_"
                try:
                    imgs = [f for f in os.listdir(q_dir) if f.startswith(prefix)]
                    imgs.sort()
                    for img in imgs:
                        img_path = q_dir / img
                        if img_path.stat().st_size == 63492:
                            continue
                        q["images"].append(f"/images/{paper_basename}/{img}")
                except Exception as e:
                    logger.warning("Error reading images for Q%s: %s", q_num, e)

        logger.info("Loaded %s questions into RAM.", f"{len(QUESTIONS_RAM):,}")
    except Exception as e:
        logger.critical("Critical failure reading question bank: %s", e, exc_info=True)
        QUESTIONS_RAM = []


def get_questions_ram() -> List[dict]:
    return QUESTIONS_RAM
