"""
Validation Agent — checks document completeness, required checklist, signature detection.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict, List

logger = logging.getLogger("tendersense.validation_agent")

VALIDATION_PROMPT = """You are a document validation officer for government procurement.

REQUIRED DOCUMENTS CHECKLIST:
{required_docs}

SUBMITTED DOCUMENTS:
{submitted_docs}

OCR TEXT SAMPLES:
{ocr_text}

YOUR TASK:
1. Check each required document type is present in submitted docs.
2. For present documents:
   - Check if document appears signed (look for "Authorized Signatory", signature marks, seal references).
   - Check dates are valid (not expired, within reasonable range).
   - Check if document name/entity matches bidder company name.
   - Flag Document Type Mismatch (e.g., uploading a CA Cert when Balance Sheet is requested).
3. Flag documents with suspicious patterns (e.g., Duplicate documents uploaded to different slots).

OUTPUT (valid JSON only):
{{
  "status": "pass|fail|needs_review",
  "confidence": 0.0-1.0,
  "criteria_results": [
    {{
      "criterion_id": "DOC_1",
      "result": "pass|fail|partial",
      "extracted_value": "Balance Sheet FY24 present and signed",
      "required_value": "Balance Sheet (last 3 years)",
      "source_text_chunk": "Audited Balance Sheet for the Financial Year 2023-2024.",
      "source_page_number": 1,
      "evidence": ["balance_sheet_fy24.pdf:page:1"],
      "explanation": "Document present, signed by CA with UDIN visible."
    }}
  ],
  "missing_documents": [],
  "unsigned_documents": [],
  "agent_reasoning": "All required documents present and validated.",
  "red_flags": []
}}"""


class ValidationAgent:
    def __init__(self, llm):
        self.llm = llm

    async def evaluate(
        self,
        required_documents: List[str],
        bidder_documents: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        start = time.time()

        submitted = [
            {
                "id": str(d.get("id")),
                "type": d.get("document_type"),
                "filename": d.get("file_name"),
                "ocr_status": d.get("ocr_status"),
                "is_signed": d.get("is_signed"),
                "checksum": d.get("checksum"),
                "expiry_date": str(d.get("expiry_date")) if d.get("expiry_date") else None,
            }
            for d in bidder_documents
        ]

        # Sample OCR text (first 500 chars per doc)
        ocr_samples = "\n\n---\n\n".join(
            f"[{d.get('file_name')}]: {(d.get('ocr_text') or '')[:500]}"
            for d in bidder_documents
            if d.get("ocr_text")
        ) or "No OCR text available."

        prompt = VALIDATION_PROMPT.format(
            required_docs=json.dumps(required_documents, indent=2),
            submitted_docs=json.dumps(submitted, indent=2),
            ocr_text=ocr_samples[:4000],
        )

        try:
            resp = await self.llm.ainvoke(prompt)
            content = resp.content if hasattr(resp, "content") else str(resp)
            result = self._parse_json(content)
            result["execution_time_ms"] = int((time.time() - start) * 1000)
            return result
        except Exception as exc:
            logger.error(f"ValidationAgent error: {exc}")
            return self._error_result(str(exc), int((time.time() - start) * 1000))

    def _parse_json(self, text: str) -> dict:
        match = re.search(r'\{.*\}', text.strip(), re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        return json.loads(text.strip())

    def _error_result(self, reason: str, ms: int) -> dict:
        return {
            "status": "needs_review",
            "confidence": 0.0,
            "criteria_results": [],
            "missing_documents": [],
            "unsigned_documents": [],
            "agent_reasoning": f"API or Parsing Error: {reason}",
            "red_flags": [f"AI Error: {reason}"],
            "execution_time_ms": ms,
        }
