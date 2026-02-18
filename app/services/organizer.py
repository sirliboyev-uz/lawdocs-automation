"""File organization: move processed documents into a structured folder tree."""

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

CATEGORY_FOLDERS: dict[str, str] = {
    "Deposition Transcript": "transcripts",
    "Contract":              "contracts",
    "Court Filing":          "court_filings",
    "Correspondence":        "correspondence",
    "Invoice":               "invoices",
    "Medical Record":        "medical_records",
    "Police Report":         "police_reports",
    "Expert Report":         "expert_reports",
    "Other":                 "other",
}


def organize_document(
    source_path: Path,
    case_name: str,
    category: str,
    original_filename: str,
) -> Path:
    """Move a document into the organized case folder. Returns the new path."""
    folder_name = CATEGORY_FOLDERS.get(category, "other")
    safe_case = _sanitize(case_name)

    target_dir = settings.storage_dir / safe_case / folder_name
    target_dir.mkdir(parents=True, exist_ok=True)

    date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stem = _sanitize(Path(original_filename).stem)
    ext = Path(original_filename).suffix.lower()
    target_path = target_dir / f"{date_prefix}_{stem}{ext}"

    counter = 1
    while target_path.exists():
        target_path = target_dir / f"{date_prefix}_{stem}_{counter}{ext}"
        counter += 1

    shutil.move(str(source_path), str(target_path))
    logger.info("Organized: %s → %s", original_filename, target_path)
    return target_path


def _sanitize(name: str) -> str:
    """Make a string safe for use as a file/directory name."""
    cleaned = "".join(c if c.isalnum() or c in "-_ " else "_" for c in name)
    return cleaned.strip().replace(" ", "_").lower()
