"""
Finance Agent — validates turnover, net worth, profit/loss from audited documents.
Uses Claude Sonnet 4 with structured JSON output for deterministic extraction.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List
from utils.currency import normalize_to_crores

logger = logging.getLogger("tendersense.finance_agent")

FINANCE_PROMPT = """You are a senior Chartered Accountant evaluating a government tender bidder's financial eligibility.

TENDER FINANCIAL CRITERIA:
{criteria}

BIDDER DECLARED VALUES:
{declared}

EXTRACTED OCR TEXT FROM FINANCIAL DOCUMENTS:
{ocr_text}

YOUR TASK:
1. Extract exact numerical values for each financial criterion from the OCR text.
2. NORMALIZE all extracted currency values to Crores (Cr) before comparison using standard conversions (e.g. 52,00,000 = 0.52 Cr, 52 lakhs = 0.52 Cr).
3. Compare extracted normalized values against the criteria requirements.
4. If a value is not found in documents, mark result as "fail" with explanation.
5. Validate consistency: declared values must match extracted values within 5% tolerance.

OUTPUT (valid JSON only, no markdown):
{{
  "status": "pass|fail|needs_review",
  "confidence": 0.0-1.0,
  "criteria_results": [
    {{
      "criterion_id": "F1",
      "result": "pass|fail|partial",
      "extracted_value": "₹187.4 Cr (3-yr avg FY22-FY24)",
      "required_value": "≥ ₹150 Cr",
      "source_text_chunk": "The average annual turnover for the past 3 financial years is ₹187.40 Crores.",
      "source_page_number": 4,
      "evidence": ["page:4", "page:6"],
      "explanation": "Average of FY22 (₹165Cr), FY23 (₹182Cr), FY24 (₹215Cr) = ₹187.4Cr. Exceeds threshold by 24.9%."
    }}
  ],
  "agent_reasoning": "Overall financial health is strong. All criteria met with documented evidence.",
  "red_flags": []
}}"""


class FinanceAgent:
    def __init__(self, llm):
        self.llm = llm

    async def evaluate(
        self,
        criteria: List[Dict[str, Any]],
        bidder_data: Dict[str, Any],
        vector_store=None,
    ) -> Dict[str, Any]:
        """
        Evaluate bidder financial criteria.
        Returns AgentVerdict dict.
        """
        import time
        start = time.time()

        # Gather OCR text from financial documents
        docs = bidder_data.get("documents", [])
        financial_docs = [
            d for d in docs
            if d.get("document_type") in ("balance_sheet", "ca_certificate", "other")
            and d.get("ocr_text")
        ]
        ocr_text = "\n\n---\n\n".join(
            f"[DOC: {d.get('document_type')} | {d.get('file_name')}]\n{d.get('ocr_text', '')[:3000]}"
            for d in financial_docs
        ) or "No financial documents extracted."

        declared = {
            "turnover_3yr": bidder_data.get("declared_turnover", []),
            "net_worth": bidder_data.get("declared_net_worth"),
        }

        prompt = FINANCE_PROMPT.format(
            criteria=json.dumps(criteria, indent=2),
            declared=json.dumps(declared, indent=2),
            ocr_text=ocr_text[:6000],
        )

        try:
            resp = await self.llm.ainvoke(prompt)
            content = resp.content if hasattr(resp, "content") else str(resp)

            # Extract JSON from response
            result = self._parse_json(content)
            result["execution_time_ms"] = int((time.time() - start) * 1000)
            return result
        except Exception as exc:
            logger.error(f"FinanceAgent error: {exc}")
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
            "agent_reasoning": f"API or Parsing Error: {reason}",
            "red_flags": [f"AI Error: {reason}"],
            "execution_time_ms": ms,
        }
