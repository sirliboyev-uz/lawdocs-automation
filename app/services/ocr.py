"""Text extraction: native PDF parsing with OCR fallback for scanned documents."""

import logging
from pathlib import Path

import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif"}
MIN_TEXT_DENSITY = 50  # chars per page to consider "has text"


def extract_text(file_path: Path) -> tuple[str, int]:
    """Extract text from a document. Returns (text, page_count)."""
    ext = file_path.suffix.lower()

    if ext in IMAGE_EXTENSIONS:
        return _ocr_image(file_path), 1

    if ext == ".pdf":
        return _extract_pdf(file_path)

    raise ValueError(f"Unsupported file type: {ext}")


def _extract_pdf(file_path: Path) -> tuple[str, int]:
    """Extract text from PDF, falling back to OCR for scanned pages."""
    pages_text: list[str] = []

    with pdfplumber.open(file_path) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages_text.append(text)

    combined = "\n\n".join(pages_text)
    avg_chars = len(combined) / max(page_count, 1)

    if avg_chars < MIN_TEXT_DENSITY:
        logger.info(
            "Low text density (%.0f chars/page), running OCR on %s",
            avg_chars, file_path.name,
        )
        return _ocr_pdf(file_path), page_count

    return combined, page_count


def _ocr_pdf(file_path: Path) -> str:
    """OCR a scanned PDF by converting pages to images first."""
    images = convert_from_path(file_path, dpi=300)
    pages_text = [pytesseract.image_to_string(img) for img in images]
    return "\n\n".join(pages_text)


def _ocr_image(file_path: Path) -> str:
    """OCR a single image file."""
    image = Image.open(file_path)
    return pytesseract.image_to_string(image)
