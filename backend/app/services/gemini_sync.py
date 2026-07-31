import logging
import os

from google import genai

from app.config import PAPERS_DIR

logger = logging.getLogger("tutor.boot")


async def synchronize_file_search_store(app) -> None:
    """Audit and mount reference assets into the Gemini File Store."""
    logger.info("Indexing multimodal reference materials into Google File Search Store...")
    client = genai.Client()

    existing_files = {f.display_name: f.name for f in client.files.list()}
    logger.debug("Found %s files already cached in Google File Store.", len(existing_files))
    app.state.file_store_registry = {}

    if not PAPERS_DIR.exists():
        logger.warning("Corpus folder '%s' not found — skipping asset registration.", PAPERS_DIR)
        return

    supported_extensions = (".pdf", ".json")
    uploaded_count = 0
    cached_count = 0

    for root, _, files in os.walk(PAPERS_DIR):
        for file in files:
            if not file.endswith(supported_extensions):
                continue

            local_path = os.path.join(root, file)
            if file in existing_files:
                logger.debug("   [CACHE HIT ] %s", file)
                app.state.file_store_registry[file] = existing_files[file]
                cached_count += 1
            else:
                try:
                    logger.info("   [UPLOADING ] %s ...", file)
                    uploaded_artifact = client.files.upload(file=local_path)
                    app.state.file_store_registry[file] = uploaded_artifact.name
                    logger.info("   [UPLOADED  ] %s → %s", file, uploaded_artifact.name)
                    uploaded_count += 1
                except Exception as upload_error:
                    logger.error("   [FAILED    ] %s: %s", file, upload_error, exc_info=True)

    logger.info(
        "File Store synced — %s cached, %s uploaded, %s total active mappings.",
        cached_count,
        uploaded_count,
        len(app.state.file_store_registry),
    )
