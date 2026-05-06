"""Pydantic models — Tenders"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class FinancialCriterion(BaseModel):
    id: str
    description: str
    min_value: Optional[float] = None
    unit: str = "INR"
    years: int = 3


class TechnicalCriterion(BaseModel):
    id: str
    description: str
    min_projects: int = 1
    min_value: Optional[float] = None
    years: int = 7


class ComplianceCriterion(BaseModel):
    id: str
    description: str
    certificate_type: str
    mandatory: bool = True


class TenderCriteria(BaseModel):
    financial: List[FinancialCriterion] = []
    technical: List[TechnicalCriterion] = []
    compliance: List[ComplianceCriterion] = []
    required_documents: List[str] = []


class TenderCreate(BaseModel):
    tender_number: str
    title: str
    department: str
    tender_type: str = "construction"
    issue_date: date
    submission_deadline: datetime
    estimated_value: Optional[float] = None
    language: str = "english"


class TenderOut(BaseModel):
    id: UUID
    tender_number: str
    title: str
    department: str
    tender_type: str
    estimated_value: Optional[float]
    issue_date: date
    submission_deadline: datetime
    language: str
    status: str
    criteria: Optional[TenderCriteria]
    uploaded_by: Optional[UUID]
    created_at: datetime

    class Config:
        from_attributes = True
