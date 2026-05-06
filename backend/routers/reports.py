"""Reports router — PDF export"""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from auth.supabase_auth import UserContext, check_permission
from services.evaluation_service import EvaluationService

router = APIRouter()
eval_svc = EvaluationService()


@router.get("/{tender_id}/pdf")
async def export_pdf_report(
    tender_id: str,
    user: UserContext = Depends(check_permission("export")),
):
    """Generate and stream a PDF evaluation report."""
    try:
        pdf_bytes = await eval_svc.generate_report(tender_id)
    except ValueError as ve:
        raise HTTPException(404, str(ve))
    except Exception as exc:
        raise HTTPException(500, f"PDF generation failed: {exc}")

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="TenderSense_Evaluation_{tender_id}.pdf"'
        },
    )
