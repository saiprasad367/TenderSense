"""Bidders router"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from auth.supabase_auth import UserContext, verify_token
from services.document_service import DocumentService

router = APIRouter()
doc_svc = DocumentService()


@router.get("")
async def list_bidders(email: str = None, user: UserContext = Depends(verify_token)):
    if email:
        # A bidder can only fetch their own applications, or an admin can fetch any.
        if user.role == "viewer" and user.email != email:
            raise HTTPException(403, "Forbidden: Can only fetch your own applications")
        bidders = await doc_svc.get_bidders_by_email(email)
        return bidders
    return []

@router.get("/{bidder_id}")
async def get_bidder(bidder_id: str, user: UserContext = Depends(verify_token)):
    bidder = await doc_svc.get_bidder_with_documents(bidder_id)
    if not bidder:
        raise HTTPException(404, "Bidder not found")
    return bidder
