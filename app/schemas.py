from datetime import datetime

from pydantic import BaseModel


# ── Cases ──────────────────────────────────────────

class CaseCreate(BaseModel):
    name: str
    description: str = ""


class CaseResponse(BaseModel):
    id: int
    name: str
    description: str
    created_at: datetime
    document_count: int = 0

    model_config = {"from_attributes": True}


# ── Documents ──────────────────────────────────────

class DocumentResponse(BaseModel):
    id: int
    case_id: int
    original_filename: str
    file_type: str
    category: str
    status: str
    page_count: int
    created_at: datetime
    error_message: str = ""

    model_config = {"from_attributes": True}


class DocumentDetail(DocumentResponse):
    raw_text: str
    stored_path: str


# ── Drafts ─────────────────────────────────────────

class DraftRequest(BaseModel):
    draft_type: str  # summary | checklist | cover_letter
    document_ids: list[int] = []  # empty → use all completed docs


class DraftResponse(BaseModel):
    id: int
    case_id: int
    draft_type: str
    title: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
