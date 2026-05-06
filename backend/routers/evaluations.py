"""Evaluations router — SSE stream evaluation, results, explanation chain"""
from __future__ import annotations

import asyncio
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from auth.supabase_auth import UserContext, check_permission, verify_token
from agents.orchestrator import OrchestratorAgent
from services.evaluation_service import EvaluationService
from services.tender_service import TenderService
from services.document_service import DocumentService

router = APIRouter()
eval_svc = EvaluationService()
tender_svc = TenderService()
doc_svc = DocumentService()

# Shared orchestrator (initialized once)
_orchestrator: Optional[OrchestratorAgent] = None


def get_orchestrator() -> OrchestratorAgent:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = OrchestratorAgent()
    return _orchestrator


class StartEvalBody(BaseModel):
    bidder_ids: Optional[List[str]] = None


@router.post("/{tender_id}/start")
async def start_evaluation(
    tender_id: str,
    body: Optional[StartEvalBody] = None,
    user: UserContext = Depends(check_permission("evaluate")),
):
    """
    Start multi-agent evaluation — returns Server-Sent Event stream.
    Frontend Evaluation.tsx connects to this endpoint for live agent progress.
    """
    dept = None if user.role == "admin" else user.department
    tender = await tender_svc.get_by_id(tender_id, dept)
    if not tender:
        raise HTTPException(404, "Tender not found")

    bidders = await doc_svc.get_bidders_for_tender(tender_id)
    if body and body.bidder_ids:
        bidders = [b for b in bidders if str(b["id"]) in body.bidder_ids]

    if not bidders:
        raise HTTPException(400, "No eligible bidders found for evaluation")

    orchestrator = get_orchestrator()

    async def event_generator():
        yield f"data: {json.dumps({'type': 'start', 'total_bidders': len(bidders)})}\n\n"

        for idx, bidder in enumerate(bidders):
            yield f"data: {json.dumps({'type': 'bidder_start', 'current': idx + 1, 'total': len(bidders), 'bidder_name': bidder.get('company_name'), 'bidder_id': str(bidder['id'])})}\n\n"

            try:
                async for update in orchestrator.evaluate_bidder(tender, bidder):
                    yield f"data: {json.dumps(update)}\n\n"
                    await asyncio.sleep(0)  # yield control
            except Exception as exc:
                yield f"data: {json.dumps({'type': 'error', 'bidder_id': str(bidder['id']), 'message': str(exc)})}\n\n"

        yield f"data: {json.dumps({'type': 'complete', 'total_bidders': len(bidders)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )


@router.get("/{tender_id}/results")
async def get_results(
    tender_id: str,
    verdict_filter: Optional[str] = None,
    user: UserContext = Depends(verify_token),
):
    results = await eval_svc.get_results(tender_id, verdict_filter)
    eligible = sum(1 for r in results if r.get("final_verdict") == "eligible")
    not_elig = sum(1 for r in results if r.get("final_verdict") == "not_eligible")
    review = sum(1 for r in results if r.get("final_verdict") == "needs_review")
    return {
        "tender_id": tender_id,
        "total_bidders": len(results),
        "eligible": eligible,
        "not_eligible": not_elig,
        "needs_review": review,
        "results": results,
    }


@router.get("/explanation/{evaluation_id}")
async def get_explanation(evaluation_id: str, user: UserContext = Depends(verify_token)):
    chain = await eval_svc.get_explanation_chain(evaluation_id)
    if not chain:
        raise HTTPException(404, "Evaluation not found")
    return chain
