"""
Compliance Agent — validates GST, ISO, labour licenses, statutory certificates.
Calls external GST/MCA APIs with graceful degradation.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict, List

from utils.external_apis import verify_gstin, lookup_mca_company

logger = logging.getLogger("tendersense.compliance_agent")

COMPLIANCE_PROMPT = """You are a legal compliance officer evaluating a government tender bidder.

TENDER COMPLIANCE CRITERIA:
{criteria}

BIDDER REGISTRATION DATA:
{reg_data}

LIVE API VERIFICATION RESULTS:
{api_results}

EXTRACTED OCR TEXT FROM CERTIFICATES:
{ocr_text}

YOUR TASK:
1. For each criterion, check if the bidder meets it based on extracted docs and API results.
2. Check certificate validity dates — expired certificates = fail.
3. Flag where API returned "needs_manual_verification".
4. GST defaults in last 3 years = automatic fail.
5. IF EMD (Earnest Money Deposit) is required: extract BG number, issuing bank, amount, and expiry date from Bank Guarantee documents. Ensure amount and expiry meet tender requirements.

OUTPUT (valid JSON only):
{{
  "status": "pass|fail|needs_review",
  "confidence": 0.0-1.0,
  "criteria_results": [
    {{
      "criterion_id": "C1",
      "result": "pass|fail|partial",
      "extracted_value": "ISO 9001:2015 valid until 2027-08-15",
      "required_value": "Valid ISO 9001:2015",
      "source_text_chunk": "This certificate is valid from 2024-08-15 until 2027-08-15.",
      "source_page_number": 1,
      "evidence": ["ISO_Certificate.pdf:page:1"],
      "explanation": "Certificate is valid. We don't just read what the bidder claimed on their certificate — we verify it against the Government of India's live GST database at the moment of evaluation."
    }}
  ],
  "gst_status": "active|inactive|needs_manual_verification",
  "agent_reasoning": "All compliance criteria met.",
  "red_flags": []
}}"""


class ComplianceAgent:
    def __init__(self, llm):
        self.llm = llm

    async def evaluate(
        self,
        criteria: List[Dict[str, Any]],
        bidder_data: Dict[str, Any],
        vector_store=None,
    ) -> Dict[str, Any]:
        start = time.time()

        # Live API checks
        api_results: Dict[str, Any] = {}
        gstin = bidder_data.get("gstin", "")
        cin = bidder_data.get("cin", "")

        if gstin:
            api_results["gst"] = await verify_gstin(gstin)
        if cin:
            api_results["mca"] = await lookup_mca_company(cin)

        # OCR from compliance docs
        docs = bidder_data.get("documents", [])
        comp_docs = [
            d for d in docs
            if d.get("document_type") in (
                "gst_certificate", "iso_certificate", "labour_license",
                "pan_card", "other"
            ) and d.get("ocr_text")
        ]
        ocr_text = "\n\n---\n\n".join(
            f"[DOC: {d.get('document_type')} | {d.get('file_name')}]\n{d.get('ocr_text', '')[:2000]}"
            for d in comp_docs
        ) or "No compliance documents extracted."

        reg_data = {
            "gstin": gstin,
            "pan": bidder_data.get("pan", ""),
            "cin": cin,
            "company_name": bidder_data.get("company_name", ""),
        }

        prompt = COMPLIANCE_PROMPT.format(
            criteria=json.dumps(criteria, indent=2),
            reg_data=json.dumps(reg_data, indent=2),
            api_results=json.dumps(api_results, indent=2)[:3000],
            ocr_text=ocr_text[:4000],
        )

        try:
            resp = await self.llm.ainvoke(prompt)
            content = resp.content if hasattr(resp, "content") else str(resp)
            result = self._parse_json(content)
            result["execution_time_ms"] = int((time.time() - start) * 1000)
            result["api_results"] = api_results  # persist for audit
            return result
        except Exception as exc:
            logger.error(f"ComplianceAgent error: {exc}")
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
            "gst_status": "needs_manual_verification",
            "agent_reasoning": f"API or Parsing Error: {reason}",
            "red_flags": [f"AI Error: {reason}"],
            "execution_time_ms": ms,
        }
