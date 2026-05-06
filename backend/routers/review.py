"""Review queue router"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from auth.supabase_auth import UserContext, check_permission, verify_token
from services.evaluation_service import EvaluationService
from models.evaluation import ReviewSubmit

router = APIRouter()
eval_svc = EvaluationService()


@router.get("/queue")
async def get_review_queue(
    department: Optional[str] = None,
    user: UserContext = Depends(check_permission("review")),
):
    dept = department if user.role == "admin" else user.department
    queue = await eval_svc.get_review_queue(dept)
    return {"queue": queue, "total": len(queue)}


@router.post("/{evaluation_id}/submit")
async def submit_review(
    evaluation_id: str,
    body: ReviewSubmit,
    user: UserContext = Depends(check_permission("review")),
):
    if body.verdict not in ("eligible", "not_eligible"):
        raise HTTPException(400, "verdict must be 'eligible' or 'not_eligible'")

    await eval_svc.submit_review(
        evaluation_id=evaluation_id,
        verdict=body.verdict,
        notes=body.notes,
        reviewer_id=user.user_id,
        reviewer_email=user.email,
        reviewer_role=user.role,
    )
    return {"success": True, "message": "Review submitted and logged in audit trail"}
