"""API routes for commitment management."""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db, Commitment
from schemas import (
    CommitmentCreate,
    CommitmentUpdate,
    CommitmentResponse,
    RenewRequest,
    StatusSummary,
)

router = APIRouter()


def _status_for_days(days: int) -> str:
    if days < 0:
        return "expired"
    if days <= 7:
        return "urgent"
    if days <= 30:
        return "soon"
    if days <= 90:
        return "upcoming"
    return "ok"


def _to_response(c: Commitment) -> CommitmentResponse:
    days = (c.expiry_date - date.today()).days
    return CommitmentResponse(
        id=c.id,
        name=c.name,
        category=c.category,
        provider=c.provider,
        expiry_date=c.expiry_date,
        amount=c.amount,
        notes=c.notes,
        is_archived=c.is_archived,
        created_at=c.created_at,
        updated_at=c.updated_at,
        days_until_expiry=days,
        status=_status_for_days(days),
    )


@router.get("/commitments", response_model=list[CommitmentResponse])
def list_commitments(
    archived: Optional[bool] = False,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Commitment)
    if archived is not None:
        q = q.filter(Commitment.is_archived == archived)
    if category:
        q = q.filter(Commitment.category == category)
    q = q.order_by(Commitment.expiry_date.asc())
    return [_to_response(c) for c in q.all()]


@router.post("/commitments", response_model=CommitmentResponse, status_code=201)
def create_commitment(data: CommitmentCreate, db: Session = Depends(get_db)):
    c = Commitment(**data.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return _to_response(c)


@router.get("/commitments/{commitment_id}", response_model=CommitmentResponse)
def get_commitment(commitment_id: int, db: Session = Depends(get_db)):
    c = db.query(Commitment).filter(Commitment.id == commitment_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Commitment not found")
    return _to_response(c)


@router.patch("/commitments/{commitment_id}", response_model=CommitmentResponse)
def update_commitment(commitment_id: int, data: CommitmentUpdate, db: Session = Depends(get_db)):
    c = db.query(Commitment).filter(Commitment.id == commitment_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Commitment not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(c, field, value)
    db.commit()
    db.refresh(c)
    return _to_response(c)


@router.delete("/commitments/{commitment_id}", status_code=204)
def delete_commitment(commitment_id: int, db: Session = Depends(get_db)):
    c = db.query(Commitment).filter(Commitment.id == commitment_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Commitment not found")
    db.delete(c)
    db.commit()


@router.post("/commitments/{commitment_id}/renew", response_model=CommitmentResponse)
def renew_commitment(commitment_id: int, data: RenewRequest, db: Session = Depends(get_db)):
    """Renew a commitment with a new expiry date, resetting reminder flags."""
    c = db.query(Commitment).filter(Commitment.id == commitment_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Commitment not found")
    c.expiry_date = data.new_expiry_date
    c.reminder_90_sent = False
    c.reminder_30_sent = False
    c.reminder_7_sent = False
    db.commit()
    db.refresh(c)
    return _to_response(c)


@router.get("/status", response_model=StatusSummary)
def get_status_summary(db: Session = Depends(get_db)):
    commitments = db.query(Commitment).filter(Commitment.is_archived == False).all()
    summary = {"total": 0, "ok": 0, "upcoming": 0, "soon": 0, "urgent": 0, "expired": 0}
    for c in commitments:
        days = (c.expiry_date - date.today()).days
        status = _status_for_days(days)
        summary["total"] += 1
        summary[status] += 1
    return StatusSummary(**summary)


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    rows = db.query(Commitment.category).distinct().all()
    return sorted([r[0] for r in rows])
