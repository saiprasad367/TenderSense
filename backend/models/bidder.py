"""Pydantic models — Bidders & Documents"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class BidderCreate(BaseModel):
    company_name: str
    gstin: str
    pan: str
    cin: Optional[str] = None
    email: str
    phone: Optional[str] = None
    declared_turnover: Optional[List[float]] = None   # last 3 FY values
    declared_net_worth: Optional[float] = None
    bid_amount: Optional[float] = None


class DocumentOut(BaseModel):
    id: UUID
    document_type: str
    file_name: str
    file_url: str
    ocr_status: str
    extracted_data: Optional[Dict[str, Any]] = None
    is_valid: Optional[bool] = None
    expiry_date: Optional[str] = None

    class Config:
        from_attributes = True


class BidderOut(BaseModel):
    id: UUID
    tender_id: UUID
    company_name: str
    gstin: str
    pan: str
    cin: Optional[str]
    email: str
    bid_amount: Optional[float]
    evaluation_status: str
    documents: List[DocumentOut] = []
    created_at: datetime

    class Config:
        from_attributes = True
