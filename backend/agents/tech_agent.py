"""
Technical Agent — evaluates project experience using semantic embeddings + Claude reasoning.
Uses ChromaDB to find similar projects across the corpus.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("tendersense.tech_agent")

TECH_PROMPT = """You are a technical evaluation officer for government infrastructure tenders.

TENDER TECHNICAL CRITERIA:
{criteria}

BIDDER CLAIMED PROJECTS:
{projects}

SIMILAR PROJECTS FOUND IN CORPUS (from semantic search):
{similar_projects}

EXTRACTED OCR TEXT FROM EXPERIENCE CERTIFICATES:
{ocr_text}

YOUR TASK:
1. Match each claimed project against the tender's technical criteria.
2. Verify certificates: check if projects have competent-authority signatures.
3. Check project contract values and completion timelines against requirements.
4. Verify certificates explicitly: check if projects have a visible competent-authority signature with official designation.
5. Semantic similarity score > 0.8 to tender requirements = eligible project.

OUTPUT (valid JSON only):
{{
  "status": "pass|fail|needs_review",
  "confidence": 0.0-1.0,
  "criteria_results": [
    {{
      "criterion_id": "T1",
      "result": "pass|fail|partial",
      "extracted_value": "4 similar bridge projects completed FY17-FY24",
      "required_value": "≥ 2 bridge projects > ₹100Cr in last 7 years",
      "source_text_chunk": "We have successfully completed 4 bridge projects exceeding ₹100Cr in value.",
      "source_page_number": 11,
      "evidence": ["ExperienceCertificates.pdf:page:11"],
      "explanation": "4 eligible projects identified and verified against authority certificates."
    }}
  ],
  "agent_reasoning": "Bidder has substantial experience matching tender requirements.",
  "matched_projects": [],
  "red_flags": []
}}"""


class TechAgent:
    def __init__(self, llm):
        self.llm = llm

    async def evaluate(
        self,
        criteria: List[Dict[str, Any]],
        bidder_data: Dict[str, Any],
        vector_store=None,
    ) -> Dict[str, Any]:
        start = time.time()

        docs = bidder_data.get("documents", [])
        exp_docs = [
            d for d in docs
            if d.get("document_type") in ("project_completion", "work_order", "other")
            and d.get("ocr_text")
        ]
        ocr_text = "\n\n---\n\n".join(
            f"[DOC: {d.get('file_name')}]\n{d.get('ocr_text', '')[:3000]}"
            for d in exp_docs
        ) or "No experience documents extracted."

        # Semantic search for similar projects
        similar_projects = []
        if vector_store and criteria:
            query = criteria[0].get("description", "bridge project infrastructure")
            similar_projects = await vector_store.search_similar_projects(query, n_results=5)

        projects = bidder_data.get("declared_projects") or []

        prompt = TECH_PROMPT.format(
            criteria=json.dumps(criteria, indent=2),
            projects=json.dumps(projects, indent=2),
            similar_projects=json.dumps(
                [{"text": s.get("text", ""), "distance": s.get("distance")} for s in similar_projects],
                indent=2,
            )[:2000],
            ocr_text=ocr_text[:5000],
        )

        try:
            resp = await self.llm.ainvoke(prompt)
            content = resp.content if hasattr(resp, "content") else str(resp)
            result = self._parse_json(content)
            result["execution_time_ms"] = int((time.time() - start) * 1000)
            return result
        except Exception as exc:
            logger.error(f"TechAgent error: {exc}")
            return self._error_result(str(exc), int((time.time() - start) * 1000))

    def _parse_json(self, text: str) -> dict:
        import json
        import re
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
