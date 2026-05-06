"""Tenders router"""
from __future__ import annotations

import asyncio
import io
import json
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from auth.supabase_auth import UserContext, check_permission, verify_token
from services.tender_service import TenderService
from services.document_service import DocumentService

router = APIRouter()
tender_svc = TenderService()
doc_svc = DocumentService()


@router.post("/upload")
async def upload_tender(
    file: UploadFile = File(...),
    tender_number: str = Form(""),
    title: str = Form(""),
    department: str = Form(""),
    tender_type: str = Form("construction"),
    issue_date: str = Form(""),
    submission_deadline: str = Form(""),
    estimated_value: Optional[float] = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user: UserContext = Depends(check_permission("upload")),
):
    """Upload tender PDF and extract criteria using Claude Sonnet 4."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted")

    file_bytes = await file.read()
    max_bytes = 50 * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(400, f"File exceeds 50 MB limit")

    metadata = {
        "tender_number": tender_number,
        "title": title,
        "department": department or user.department,
        "tender_type": tender_type,
        "issue_date": issue_date or None,
        "submission_deadline": submission_deadline or None,
        "estimated_value": estimated_value,
    }

    tender_id = await tender_svc.upload_and_process(
        file_bytes=file_bytes,
        file_name=file.filename,
        metadata=metadata,
        uploaded_by=user.user_id,
    )
    return {"success": True, "tender_id": tender_id, "message": "Tender uploaded. Criteria extraction complete."}


@router.get("")
async def list_tenders(
    status: Optional[str] = None,
    department: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    user: UserContext = Depends(verify_token),
):
    if user.role == "viewer":
        dept = None
        # Only bidders should see these status types generally, but handled via frontend/RLS
    else:
        dept = department if user.role == "admin" else user.department
        
    tenders = await tender_svc.list(status=status, department=dept, skip=skip, limit=limit)
    return {"tenders": tenders, "total": len(tenders)}


@router.get("/{tender_id}")
async def get_tender(tender_id: str, user: UserContext = Depends(verify_token)):
    if user.role == "viewer" or user.role == "admin":
        dept = None
    else:
        dept = user.department
        
    tender = await tender_svc.get_by_id(tender_id, dept)
    if not tender:
        raise HTTPException(404, "Tender not found")
    return tender


@router.post("/{tender_id}/bidders/upload")
async def upload_bidder(
    tender_id: str,
    company_name: str = Form(...),
    gstin: str = Form(...),
    pan: str = Form(...),
    email: str = Form(...),
    cin: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    declared_turnover: Optional[str] = Form(None),   # JSON array string
    declared_net_worth: Optional[float] = Form(None),
    bid_amount: Optional[float] = Form(None),
    documents: List[UploadFile] = File([]),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user: UserContext = Depends(check_permission("upload")),
):
    """Upload bidder with all supporting documents."""
    if user.role == "viewer" or user.role == "admin":
        dept = None
    else:
        dept = user.department
        
    tender = await tender_svc.get_by_id(tender_id, dept)
    if not tender:
        raise HTTPException(404, "Tender not found")
    if tender.get("status") not in ("active", "evaluation_in_progress"):
        raise HTTPException(400, f"Tender status '{tender.get('status')}' does not accept new submissions")

    turnover = None
    if declared_turnover:
        try:
            turnover = json.loads(declared_turnover)
        except Exception:
            turnover = None

    bidder_data = {
        "company_name": company_name,
        "gstin": gstin,
        "pan": pan,
        "cin": cin,
        "email": email,
        "phone": phone,
        "declared_turnover": turnover,
        "declared_net_worth": declared_net_worth,
        "bid_amount": bid_amount,
    }

    # Read all files
    doc_list = []
    for f in documents:
        fb = await f.read()
        doc_list.append({
            "file_bytes": fb,
            "file_name": f.filename or "doc.pdf",
            "mime_type": f.content_type or "application/pdf",
        })

    bidder_id = await doc_svc.upload_bidder_package(
        tender_id=tender_id,
        bidder_data=bidder_data,
        documents=doc_list,
    )

    # OCR in background
    background_tasks.add_task(doc_svc.process_all_documents, bidder_id)

    return {"success": True, "bidder_id": bidder_id, "message": "Bidder uploaded. OCR processing started."}
