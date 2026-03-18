"""Pydantic schemas for API request/response."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class CommitmentCreate(BaseModel):
    name: str
    category: str
    provider: str = ""
    expiry_date: date
    amount: str = ""
    notes: str = ""


class CommitmentUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    provider: Optional[str] = None
    expiry_date: Optional[date] = None
    amount: Optional[str] = None
    notes: Optional[str] = None
    is_archived: Optional[bool] = None


class CommitmentResponse(BaseModel):
    id: int
    name: str
    category: str
    provider: str
    expiry_date: date
    amount: str
    notes: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    days_until_expiry: int
    status: str  # "ok", "upcoming", "soon", "urgent", "expired"

    model_config = {"from_attributes": True}


class RenewRequest(BaseModel):
    new_expiry_date: date


class StatusSummary(BaseModel):
    total: int
    ok: int
    upcoming: int
    soon: int
    urgent: int
    expired: int
