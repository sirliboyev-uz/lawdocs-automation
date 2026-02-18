"""Case management endpoints: create, list, get, delete."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Case, Document
from app.schemas import CaseCreate, CaseResponse

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=CaseResponse, status_code=201)
def create_case(payload: CaseCreate, db: Session = Depends(get_db)):
    case = Case(name=payload.name, description=payload.description)
    db.add(case)
    db.commit()
    db.refresh(case)
    return _enrich(case, db)


@router.get("", response_model=list[CaseResponse])
def list_cases(db: Session = Depends(get_db)):
    cases = db.query(Case).order_by(Case.created_at.desc()).all()
    return [_enrich(c, db) for c in cases]


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(case_id: int, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return _enrich(case, db)


@router.delete("/{case_id}", status_code=204)
def delete_case(case_id: int, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    db.delete(case)
    db.commit()


def _enrich(case: Case, db: Session) -> dict:
    """Attach computed fields to a case before serialization."""
    count = (
        db.query(func.count(Document.id))
        .filter(Document.case_id == case.id)
        .scalar()
    )
    return {
        "id": case.id,
        "name": case.name,
        "description": case.description,
        "created_at": case.created_at,
        "document_count": count,
    }
