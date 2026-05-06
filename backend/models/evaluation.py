"""Pydantic models — Evaluations"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class CriterionResult(BaseModel):
    criterion_id: str
    result: str          # "pass" | "fail" | "partial"
    evidence: List[str]  # ["doc_id:page", ...]
    explanation: str
    extracted_value: Optional[str] = None
    required_value: Optional[str] = None


class AgentVerdict(BaseModel):
    status: str          # "pass" | "fail" | "needs_review"
    confidence: float
    criteria_results: List[CriterionResult] = []
    agent_reasoning: str = ""
    execution_time_ms: int = 0


class ExplanationChain(BaseModel):
    summary: str
    criterion_analysis: List[Dict[str, Any]] = []
    risk_factors: List[str] = []
    recommendation: str


class EvaluationOut(BaseModel):
    id: UUID
    tender_id: UUID
    bidder_id: UUID
    bidder_name: str = ""
    bid_amount: Optional[float] = None
    final_verdict: str           # "eligible" | "not_eligible" | "needs_review"
    confidence_score: float
    finance_verdict: Optional[AgentVerdict]
    tech_verdict: Optional[AgentVerdict]
    compliance_verdict: Optional[AgentVerdict]
    validation_verdict: Optional[AgentVerdict]
    fraud_verdict: Optional[AgentVerdict]
    explanation_chain: Optional[ExplanationChain]
    needs_human_review: bool
    review_reason: str = ""
    human_verdict: Optional[str] = None
    human_notes: Optional[str] = None
    evaluated_at: datetime

    class Config:
        from_attributes = True


class ReviewSubmit(BaseModel):
    verdict: str   # "eligible" | "not_eligible"
    notes: str = ""
