"""
Document Service — handles bidder document uploads, OCR background processing.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from database.supabase_client import get_supabase
from utils.ocr import get_ocr_pipeline
from utils.audit_logger import AuditLogger

logger = logging.getLogger("tendersense.document_service")
audit = AuditLogger()

ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png"}
DOC_TYPE_MAP = {
    "balance_sheet": ["balance", "b/s", "financial statement"],
    "ca_certificate": ["chartered accountant", "ca certificate", "auditor"],
    "gst_certificate": ["gstin", "gst certificate", "goods and services tax"],
    "pan_card": ["permanent account number", "pan card"],
    "project_completion": ["completion certificate", "work order", "project certificate"],
    "iso_certificate": ["iso", "9001", "quality management"],
    "labour_license": ["labour", "labor", "contractor license"],
    "emd_bg": ["emd", "earnest money", "bank guarantee", "bg"],
}

# Maps our internal classification to values the DB CHECK constraint accepts.
# 'emd_bg' is classified by us but stored as 'other' until a DB migration is run.
_DB_SAFE_DOC_TYPES = {
    "balance_sheet", "ca_certificate", "gst_certificate", "pan_card",
    "project_completion", "iso_certificate", "labour_license", "other",
}

def _to_db_safe_type(doc_type: str) -> str:
    """Return the doc_type if DB-safe, else fall back to 'other'."""
    return doc_type if doc_type in _DB_SAFE_DOC_TYPES else "other"


class DocumentService:
    async def upload_bidder_package(
        self,
        tender_id: str,
        bidder_data: Dict[str, Any],
        documents: List[Dict[str, Any]],  # list of {file_bytes, file_name, mime_type}
    ) -> str:
        """
        Create bidder record and upload all documents to Supabase Storage.
        Returns bidder_id.
        """
        sb = get_supabase()
        bidder_id = str(uuid4())

        # Create bidder record
        bidder_row = {
            "id": bidder_id,
            "tender_id": tender_id,
            "company_name": bidder_data.get("company_name"),
            "gstin": bidder_data.get("gstin"),
            "pan": bidder_data.get("pan"),
            "cin": bidder_data.get("cin"),
            "email": bidder_data.get("email"),
            "phone": bidder_data.get("phone"),
            "declared_turnover": bidder_data.get("declared_turnover"),
            "declared_net_worth": bidder_data.get("declared_net_worth"),
            "bid_amount": bidder_data.get("bid_amount"),
            "evaluation_status": "pending",
        }
        # SELECT-FIRST pattern: check if this bidder (tender_id + gstin) already exists
        # from a previous failed attempt. If yes, reuse their ID and skip to document upload.
        # We avoid upsert/update because it triggers a FK violation when documents already
        # reference the old bidder_id.
        gstin = bidder_data.get("gstin", "")
        existing_res = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: sb.table("bidders")
            .select("id")
            .eq("tender_id", tender_id)
            .eq("gstin", gstin)
            .limit(1)
            .execute()
        )
        if existing_res.data:
            # Bidder already exists — reuse their ID for document uploads
            bidder_id = existing_res.data[0]["id"]
            logger.info(f"Resuming upload for existing bidder {bidder_id} (GSTIN: {gstin})")
        else:
            # New bidder — insert fresh row
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: sb.table("bidders").insert(bidder_row).execute()
            )

        # Upload each document
        doc_ids = []
        for doc in documents:
            doc_id = await self._upload_single_document(bidder_id, doc)
            if doc_id:
                doc_ids.append(doc_id)

        await audit.log(
            entity_type="bidder",
            entity_id=bidder_id,
            action="CREATED",
            new_value={
                "company_name": bidder_data.get("company_name"),
                "gstin": bidder_data.get("gstin"),
                "doc_count": len(doc_ids),
            },
        )
        logger.info(f"Bidder {bidder_id} created with {len(doc_ids)} documents")
        return bidder_id

    async def _upload_single_document(
        self, bidder_id: str, doc: Dict[str, Any]
    ) -> Optional[str]:
        sb = get_supabase()
        file_bytes: bytes = doc.get("file_bytes", b"")
        file_name: str = doc.get("file_name", "document.pdf")
        mime_type: str = doc.get("mime_type", "application/pdf")

        if not file_bytes:
            return None

        doc_id = str(uuid4())
        storage_path = f"bidder-documents/{bidder_id}/{doc_id}_{file_name}"

        # Checksum for integrity
        checksum = hashlib.sha256(file_bytes).hexdigest()

        # Idempotency check: if this exact file was already uploaded (same checksum + bidder),
        # skip it silently. This prevents duplicate records on retry after a mid-batch failure.
        existing_doc = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: sb.table("documents")
            .select("id")
            .eq("bidder_id", bidder_id)
            .eq("checksum", checksum)
            .limit(1)
            .execute()
        )
        if existing_doc.data:
            logger.info(f"Document {file_name} already uploaded (checksum match) — skipping.")
            return existing_doc.data[0]["id"]

        # Auto-classify document type
        doc_type = self._classify_document(file_name, file_bytes)

        # Upload to Supabase Storage
        try:
            sb.storage.from_("bidder-documents").upload(
                storage_path,
                file_bytes,
                file_options={"content-type": mime_type},
            )
            public_url = sb.storage.from_("bidder-documents").get_public_url(storage_path)
        except Exception as exc:
            logger.error(f"Storage upload failed for {file_name}: {exc}")
            return None

        # Create document record
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: sb.table("documents").insert({
                "id": doc_id,
                "bidder_id": bidder_id,
                "document_type": _to_db_safe_type(doc_type),
                "file_name": file_name,
                "file_url": public_url,
                "file_path": storage_path,
                "file_size": len(file_bytes),
                "mime_type": mime_type,
                "ocr_status": "pending",
                "checksum": checksum,
            }).execute(),
        )
        return doc_id

    async def process_all_documents(self, bidder_id: str) -> None:
        """
        Background task: OCR all pending documents for a bidder.
        """
        sb = get_supabase()
        docs = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: sb.table("documents")
            .select("*")
            .eq("bidder_id", bidder_id)
            .eq("ocr_status", "pending")
            .execute(),
        )
        for doc in (docs.data or []):
            await self._ocr_document(doc)

    async def _ocr_document(self, doc: dict) -> None:
        sb = get_supabase()
        doc_id = doc["id"]

        # Mark as processing
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: sb.table("documents")
            .update({"ocr_status": "processing"})
            .eq("id", doc_id)
            .execute(),
        )

        try:
            # Download file from Supabase Storage
            file_bytes = sb.storage.from_("bidder-documents").download(doc["file_path"])

            ocr = get_ocr_pipeline()
            results = await ocr.extract_from_pdf(file_bytes)
            full_text = ocr.full_text(results)
            avg_confidence = (
                sum(r.confidence for r in results) / len(results) if results else 0.0
            )

            # Detect signature hints
            is_signed = self._detect_signature(full_text)

            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: sb.table("documents").update({
                    "ocr_status": "completed",
                    "ocr_text": full_text[:100000],  # cap at 100k chars
                    "ocr_confidence": round(avg_confidence, 4),
                    "is_signed": is_signed,
                    "processed_at": "now()",
                }).eq("id", doc_id).execute(),
            )
            logger.info(f"OCR complete for document {doc_id}")
        except Exception as exc:
            logger.error(f"OCR failed for {doc_id}: {exc}")
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: sb.table("documents")
                .update({"ocr_status": "failed"})
                .eq("id", doc_id)
                .execute(),
            )

    async def get_bidder_with_documents(self, bidder_id: str) -> Optional[Dict]:
        sb = get_supabase()
        bidder_res = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: sb.table("bidders").select("*").eq("id", bidder_id).single().execute(),
        )
        if not bidder_res.data:
            return None

        docs_res = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: sb.table("documents").select("*").eq("bidder_id", bidder_id).execute(),
        )
        bidder = bidder_res.data
        bidder["documents"] = docs_res.data or []
        return bidder

    async def get_bidders_for_tender(self, tender_id: str) -> List[Dict]:
        sb = get_supabase()
        bidders_res = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: sb.table("bidders").select("*").eq("tender_id", tender_id).execute(),
        )
        bidders = bidders_res.data or []

        # Attach documents to each bidder
        for bidder in bidders:
            docs_res = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda b=bidder: sb.table("documents")
                .select("*")
                .eq("bidder_id", b["id"])
                .execute(),
            )
            bidder["documents"] = docs_res.data or []
        return bidders

    async def get_bidders_by_email(self, email: str) -> List[Dict]:
        sb = get_supabase()
        # Get bidder applications for this email, joined with tender info
        bidders_res = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: sb.table("bidders").select("*, tender:tenders(*)").eq("email", email).order("created_at", desc=True).execute(),
        )
        return bidders_res.data or []

    @staticmethod
    def _classify_document(file_name: str, file_bytes: bytes) -> str:
        """Classify document type from filename."""
        lower = file_name.lower()
        for doc_type, keywords in DOC_TYPE_MAP.items():
            if any(kw in lower for kw in keywords):
                return doc_type
        return "other"

    @staticmethod
    def _detect_signature(text: str) -> bool:
        """Heuristic: look for signature markers in OCR text."""
        keywords = [
            "authorized signatory", "signature", "signed by",
            "seal of", "for and on behalf", "director",
            "chartered accountant", "udin",
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in keywords)
