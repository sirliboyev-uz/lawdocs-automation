"""Document upload, processing, and draft-generation endpoints."""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Case, Document, DocumentStatus, Draft
from app.schemas import DocumentDetail, DocumentResponse, DraftRequest, DraftResponse
from app.services.classifier import classify_document
from app.services.generator import generate_draft
from app.services.ocr import extract_text
from app.services.organizer import organize_document

logger = logging.getLogger(__name__)

router = APIRouter(tags=["documents"])


# ── Upload & list ──────────────────────────────────

@router.post(
    "/cases/{case_id}/documents",
    response_model=DocumentResponse,
    status_code=202,
)
def upload_document(
    case_id: int,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    ext = Path(file.filename or "unknown").suffix.lower()
    if ext not in settings.supported_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported: {settings.supported_extensions}",
        )

    # Persist the upload to a temp location
    upload_dir = settings.storage_dir / "_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_path = upload_dir / f"{uuid.uuid4()}{ext}"

    content = file.file.read()
    if len(content) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds {settings.max_upload_size_mb} MB limit",
        )
    temp_path.write_bytes(content)

    doc = Document(
        case_id=case_id,
        original_filename=file.filename or "unknown",
        stored_path=str(temp_path),
        file_type=ext,
        status=DocumentStatus.pending,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    background_tasks.add_task(_process_document, doc.id, case.name, temp_path)
    return doc


@router.get("/cases/{case_id}/documents", response_model=list[DocumentResponse])
def list_documents(case_id: int, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return (
        db.query(Document)
        .filter(Document.case_id == case_id)
        .order_by(Document.created_at.desc())
        .all()
    )


@router.get("/documents/{doc_id}", response_model=DocumentDetail)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


# ── Draft generation ───────────────────────────────

@router.post(
    "/cases/{case_id}/generate",
    response_model=DraftResponse,
    status_code=201,
)
def generate_case_draft(
    case_id: int,
    payload: DraftRequest,
    db: Session = Depends(get_db),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    query = db.query(Document).filter(
        Document.case_id == case_id,
        Document.status == DocumentStatus.completed,
    )
    if payload.document_ids:
        query = query.filter(Document.id.in_(payload.document_ids))

    documents = query.all()
    if not documents:
        raise HTTPException(
            status_code=400,
            detail="No completed documents found for this case",
        )

    doc_data = [
        {
            "filename": d.original_filename,
            "category": d.category,
            "text": d.raw_text,
        }
        for d in documents
    ]

    title, content = generate_draft(payload.draft_type, case.name, doc_data)

    draft = Draft(
        case_id=case_id,
        draft_type=payload.draft_type,
        title=title,
        content=content,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


@router.get("/cases/{case_id}/drafts", response_model=list[DraftResponse])
def list_drafts(case_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Draft)
        .filter(Draft.case_id == case_id)
        .order_by(Draft.created_at.desc())
        .all()
    )


# ── Background processing ─────────────────────────

def _process_document(doc_id: int, case_name: str, file_path: Path):
    """Background pipeline: Extract → Classify → Organize."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return

        doc.status = DocumentStatus.processing
        db.commit()

        # Step 1 — Extract text
        raw_text, page_count = extract_text(file_path)
        doc.raw_text = raw_text
        doc.page_count = page_count

        # Step 2 — Classify
        category = classify_document(raw_text)
        doc.category = category

        # Step 3 — Organize into folder structure
        new_path = organize_document(
            file_path, case_name, category, doc.original_filename,
        )
        doc.stored_path = str(new_path)

        doc.status = DocumentStatus.completed
        db.commit()
        logger.info(
            "Processed document %d: %s → %s", doc_id, doc.original_filename, category,
        )

    except Exception as exc:
        logger.exception("Failed to process document %d", doc_id)
        doc.status = DocumentStatus.failed
        doc.error_message = str(exc)
        db.commit()
    finally:
        db.close()
