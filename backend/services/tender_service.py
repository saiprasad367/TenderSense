"""
Tender Service — CRUD operations, Supabase Storage upload, criteria extraction via Claude.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
from uuid import uuid4
from fastapi import HTTPException

from database.supabase_client import get_supabase
from utils.ocr import get_ocr_pipeline
from utils.audit_logger import AuditLogger

logger = logging.getLogger("tendersense.tender_service")
audit = AuditLogger()

CRITERIA_EXTRACTION_PROMPT = """You are an expert government procurement analyst.

Analyze this tender document text and extract ALL eligibility criteria in structured JSON.

TENDER TEXT:
{text}

Extract criteria in this exact structure:
{{
  "financial": [
    {{"id": "F1", "description": "Minimum average annual turnover", "min_value": 150000000, "unit": "INR", "years": 3}}
  ],
  "technical": [
    {{"id": "T1", "description": "Similar project experience", "min_projects": 2, "min_value": 100000000, "years": 7}}
  ],
  "compliance": [
    {{"id": "C1", "description": "ISO 9001:2015 certification", "certificate_type": "iso", "mandatory": true}}
  ],
  "required_documents": [
    "balance_sheet", "ca_certificate", "gst_certificate", "pan_card",
    "project_completion", "iso_certificate", "labour_license"
  ]
}}

Return ONLY valid JSON, no markdown, no commentary."""


class TenderService:
    def __init__(self):
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            from dotenv import load_dotenv
            load_dotenv(override=True)
            from langchain_openai import ChatOpenAI
            self._llm = ChatOpenAI(
                model=os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4"),
                api_key=os.getenv("OPENROUTER_API_KEY", ""),
                base_url="https://openrouter.ai/api/v1",
                temperature=0.0,
                max_tokens=2000,
                default_headers={
                    "HTTP-Referer": "https://tendersense.ai",
                    "X-Title": "TenderSense AI",
                },
            )
        return self._llm

    async def upload_and_process(
        self,
        file_bytes: bytes,
        file_name: str,
        metadata: Dict[str, Any],
        uploaded_by: str,
    ) -> str:
        """
        Upload PDF to Supabase Storage, extract text, extract criteria via Claude.
        Returns tender_id.
        """
        sb = get_supabase()
        tender_id = str(uuid4())
        storage_path = f"tenders/{tender_id}/{file_name}"

        # Upload to Supabase Storage
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: sb.storage.from_("tender-documents").upload(
                    storage_path,
                    file_bytes,
                    file_options={"content-type": "application/pdf"},
                )
            )
            public_url = sb.storage.from_("tender-documents").get_public_url(storage_path)
        except Exception as exc:
            logger.error(f"Supabase Storage upload failed: {exc}")
            raise HTTPException(500, f"Failed to upload document to storage. Ensure 'tender-documents' bucket exists. Error: {exc}")

        # OCR extraction
        ocr = get_ocr_pipeline()
        ocr_results = await ocr.extract_from_pdf(file_bytes)
        full_text = ocr.full_text(ocr_results)

        # Criteria extraction via Claude
        criteria = await self._extract_criteria(full_text[:8000])

        # Determine language
        language = "english"
        if re.search(r"[\u0C80-\u0CFF]", full_text):  # Kannada Unicode range
            language = "bilingual"

        # Ensure tender_number is strictly unique by appending a short ID during testing
        t_num = metadata.get("tender_number", "").strip()
        if not t_num:
            t_num = f"TND-{tender_id[:8].upper()}"
        else:
            t_num = f"{t_num}-{tender_id[:4].upper()}"

        row = {
            "id": tender_id,
            "tender_number": t_num,
            "title": metadata.get("title", "Untitled Tender") or "Untitled Tender",
            "department": metadata.get("department", ""),
            "tender_type": metadata.get("tender_type", "construction"),
            "tender_document_url": public_url,
            "tender_document_path": storage_path,
            "criteria": criteria,
            "issue_date": metadata.get("issue_date"),
            "submission_deadline": metadata.get("submission_deadline"),
            "estimated_value": metadata.get("estimated_value"),
            "language": language,
            "status": "active",
            "uploaded_by": uploaded_by,
        }
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: sb.table("tenders").insert(row).execute(),
        )

        await audit.log(
            entity_type="tender",
            entity_id=tender_id,
            action="CREATED",
            user_id=uploaded_by,
            new_value={"tender_number": row["tender_number"], "title": row["title"]},
        )

        logger.info(f"Tender {tender_id} created from {file_name}")
        
        return tender_id



    async def _extract_criteria(self, text: str) -> dict:
        try:
            llm = self._get_llm()
            prompt = CRITERIA_EXTRACTION_PROMPT.format(text=text)
            resp = await llm.ainvoke(prompt)
            content = resp.content if hasattr(resp, "content") else str(resp)
            content = re.sub(r"```json\s*", "", content)
            content = re.sub(r"```\s*", "", content)
            return json.loads(content.strip())
        except Exception as exc:
            logger.error(f"Criteria extraction failed: {exc}")
            return {
                "financial": [], "technical": [], "compliance": [],
                "required_documents": [
                    "balance_sheet", "gst_certificate", "pan_card",
                    "project_completion", "iso_certificate",
                ],
            }

    async def get_by_id(self, tender_id: str, department: Optional[str] = None) -> Optional[Dict]:
        sb = get_supabase()
        q = sb.table("tenders").select("*").eq("id", tender_id)
        if department:
            q = q.eq("department", department)
        res = await asyncio.get_event_loop().run_in_executor(None, lambda: q.execute())
        return res.data[0] if res.data else None

    async def list(
        self,
        status: Optional[str] = None,
        department: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Dict]:
        sb = get_supabase()
        q = sb.table("tenders").select("*").order("created_at", desc=True)
        if status:
            q = q.eq("status", status)
        if department:
            q = q.eq("department", department)
        q = q.range(skip, skip + limit - 1)
        res = await asyncio.get_event_loop().run_in_executor(None, lambda: q.execute())
        return res.data or []

    async def update_status(self, tender_id: str, status: str) -> None:
        sb = get_supabase()
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: sb.table("tenders").update({"status": status}).eq("id", tender_id).execute(),
        )
