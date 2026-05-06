"""Analytics router — dashboard stats"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from auth.supabase_auth import UserContext, verify_token
from services.evaluation_service import EvaluationService

router = APIRouter()
eval_svc = EvaluationService()


@router.get("/dashboard")
async def dashboard_analytics(
    department: Optional[str] = None,
    user: UserContext = Depends(verify_token),
):
    """Dashboard analytics — counts, recent evaluations, activity."""
    dept = department if user.role == "admin" else user.department
    return await eval_svc.get_analytics(dept)
