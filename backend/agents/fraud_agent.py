"""
Fraud Agent — cross-bidder anomaly detection using cosine similarity + Claude reasoning.
Detects: duplicate projects, document tampering, turnover anomalies, bid-ring patterns.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict, List

logger = logging.getLogger("tendersense.fraud_agent")

FRAUD_PROMPT = """You are a forensic auditor specializing in government procurement fraud detection.

BIDDER DATA:
{bidder_data}

CROSS-BIDDER SIMILARITY RESULTS (ChromaDB cosine similarity):
{cross_similar}

DECLARED vs VERIFIED FINANCIAL DISCREPANCY:
{financial_delta}

OCR DOCUMENT SAMPLES:
{ocr_text}

YOUR TASK — detect these fraud patterns:
1. Duplicate project claims: same project claimed by multiple bidders (high cosine similarity).
2. Document tampering: DPI inconsistencies, font changes, metadata anomalies.
3. Turnover anomalies: declared values diverge from MCA-filed data by >15%.
4. Shell company indicators: very new company, unusually low workforce, address overlaps.
5. Bid-ring patterns: multiple bidders with suspiciously similar bids.
6. Signature mismatches: different signatures on same certificate across pages.
7. CA Cross-bidder check: Same Chartered Accountant certifying financials for 3+ bidders in the same tender = very high risk signal. Extract CA membership number.
8. IP/Metadata Collusion: If metadata shows identical creator software, similar creation timestamps, or identical author tags across different bidders, flag as cartel ring.

RISK SCORING:
- Each confirmed fraud indicator: +20 to risk score (max 100)
- Suspected indicator: +10
- Clean record: 0

OUTPUT (valid JSON only):
{{
  "status": "pass|needs_review|fail",
  "confidence": 0.0-1.0,
  "risk_score": 0-100,
  "fraud_indicators": [
    {
      "type": "duplicate_project_claim",
      "severity": "high|medium|low",
      "description": "Project 'Coastal Span Phase 2' also claimed by bidder B-004. Cosine similarity: 0.94",
      "source_text_chunk": "Completed Coastal Span Phase 2 on August 2023.",
      "source_page_number": 6,
      "evidence": ["ProjectList.pdf:page:6"],
      "score_contribution": 20
    }
  ],
  "criteria_results": [],
  "agent_reasoning": "Multiple high-severity fraud indicators found. Recommend rejection.",
  "red_flags": ["Duplicate project claim", "Signature mismatch"]
}}"""


class FraudAgent:
    def __init__(self, llm):
        self.llm = llm

    async def evaluate(
        self,
        bidder_data: Dict[str, Any],
        documents: List[Dict[str, Any]],
        vector_store=None,
    ) -> Dict[str, Any]:
        start = time.time()

        # Cross-bidder similarity via vector store
        cross_similar = []
        if vector_store:
            bidder_id = str(bidder_data.get("id", ""))
            if bidder_id:
                cross_similar = await vector_store.cross_bidder_similarity(
                    bidder_id, field="projects", n_results=5
                )

        # Financial discrepancy: declared vs extracted
        declared_turnover = bidder_data.get("declared_turnover") or []
        extracted_data = bidder_data.get("extracted_data") or {}
        financial_delta = {
            "declared_turnover": declared_turnover,
            "extracted_turnover": extracted_data.get("turnover"),
            "discrepancy_pct": self._calc_discrepancy(
                declared_turnover, extracted_data.get("turnover")
            ),
        }

        # OCR samples for forgery detection
        ocr_text = "\n\n---\n\n".join(
            f"[{d.get('file_name')}] (page metadata: {d.get('ocr_confidence', 'N/A')})\n"
            f"{(d.get('ocr_text') or '')[:800]}"
            for d in documents
            if d.get("ocr_text")
        )[:5000] or "No OCR data."

        bidder_summary = {
            "id": str(bidder_data.get("id")),
            "company_name": bidder_data.get("company_name"),
            "gstin": bidder_data.get("gstin"),
            "pan": bidder_data.get("pan"),
        }

        prompt = FRAUD_PROMPT.format(
            bidder_data=json.dumps(bidder_summary, indent=2),
            cross_similar=json.dumps(
                [{"text": s.get("text", "")[:200], "distance": s.get("distance")} for s in cross_similar],
                indent=2,
            )[:2000],
            financial_delta=json.dumps(financial_delta, indent=2),
            ocr_text=ocr_text,
        )

        try:
            resp = await self.llm.ainvoke(prompt)
            content = resp.content if hasattr(resp, "content") else str(resp)
            result = self._parse_json(content)
            result["execution_time_ms"] = int((time.time() - start) * 1000)
            return result
        except Exception as exc:
            logger.error(f"FraudAgent error: {exc}")
            return self._error_result(str(exc), int((time.time() - start) * 1000))

    def _calc_discrepancy(self, declared: list, extracted) -> float:
        if not declared or extracted is None:
            return 0.0
        try:
            declared_avg = sum(float(v) for v in declared) / len(declared)
            extracted_val = float(extracted)
            if declared_avg == 0:
                return 0.0
            return abs(declared_avg - extracted_val) / declared_avg * 100
        except (TypeError, ValueError, ZeroDivisionError):
            return 0.0

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
            "risk_score": 50,
            "fraud_indicators": [],
            "criteria_results": [],
            "agent_reasoning": f"API or Parsing Error: {reason}",
            "red_flags": [f"AI Error: {reason}"],
            "execution_time_ms": ms,
        }
