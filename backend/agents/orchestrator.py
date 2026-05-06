"""
LangGraph Orchestrator — coordinates all 5 specialist agents and synthesizes the final verdict.
Uses parallel execution for Finance, Tech, Compliance, Fraud (after Validation completes).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, TypedDict

from langchain_openai import ChatOpenAI

from agents.finance_agent import FinanceAgent
from agents.tech_agent import TechAgent
from agents.compliance_agent import ComplianceAgent
from agents.validation_agent import ValidationAgent
from agents.fraud_agent import FraudAgent
from utils.vector_store import VectorStore
from utils.audit_logger import AuditLogger
from utils.email_service import send_evaluation_result
from database.supabase_client import get_supabase

logger = logging.getLogger("tendersense.orchestrator")

SYNTHESIS_PROMPT = """You are the final decision maker for a government tender evaluation.

TENDER CRITERIA:
{criteria}

AGENT VERDICTS SUMMARY:
- Finance Agent: status={finance_status}, confidence={finance_conf}
  Reasoning: {finance_reasoning}
  Red flags: {finance_flags}

- Technical Agent: status={tech_status}, confidence={tech_conf}
  Reasoning: {tech_reasoning}

- Compliance Agent: status={compliance_status}, confidence={compliance_conf}
  Reasoning: {compliance_reasoning}
  GST Status: {gst_status}

- Validation Agent: status={validation_status}, confidence={validation_conf}
  Missing docs: {missing_docs}

- Fraud Agent: status={fraud_status}, risk_score={fraud_risk}
  Indicators: {fraud_indicators}

RULES:
1. If ANY agent status is "fail" → final verdict must be "not_eligible"
2. If fraud risk_score > 70 → final verdict must be "not_eligible"
3. If fraud risk_score 40-70 OR any agent is "needs_review" → "needs_review"
4. If ALL agents are "pass" AND fraud risk < 40 → "eligible"
5. Confidence = weighted average (Finance 30%, Tech 30%, Compliance 20%, Validation 10%, Fraud 10%)
6. Flag for human review if: confidence < 0.85, conflicting signals, fraud indicators present

OUTPUT (valid JSON only):
{{
  "final_verdict": "eligible|not_eligible|needs_review",
  "confidence_score": 0.92,
  "explanation_chain": {{
    "summary": "Brief 1-2 sentence verdict summary",
    "criterion_analysis": [],
    "risk_factors": [],
    "recommendation": "Detailed recommendation for procurement officer"
  }},
  "needs_review": false,
  "review_reason": ""
}}"""


class OrchestratorAgent:
    def __init__(self):
        openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4")

        # OpenRouter exposes an OpenAI-compatible endpoint
        self.llm = ChatOpenAI(
            model=model,
            api_key=openrouter_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.1,
            max_tokens=4000,
            default_headers={
                "HTTP-Referer": "https://tendersense.ai",
                "X-Title": "TenderSense AI",
            },
        )

        self.finance_agent = FinanceAgent(self.llm)
        self.tech_agent = TechAgent(self.llm)
        self.compliance_agent = ComplianceAgent(self.llm)
        self.validation_agent = ValidationAgent(self.llm)
        self.fraud_agent = FraudAgent(self.llm)
        self.vector_store = VectorStore()
        self.audit_logger = AuditLogger()

    async def evaluate_bidder(
        self,
        tender: Dict[str, Any],
        bidder: Dict[str, Any],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Main evaluation entry point.
        Yields SSE-compatible progress dict objects.
        """
        start_ts = time.time()
        criteria = tender.get("criteria") or {}

        # Phase 1: Index documents into vector store
        yield {"type": "agent_start", "agent": "document_indexing", "message": "Indexing documents into vector store…"}
        try:
            await self.vector_store.index_bidder_documents(
                str(bidder.get("id")), bidder.get("documents", [])
            )
            yield {"type": "agent_complete", "agent": "document_indexing", "message": "Indexing complete"}
        except Exception as exc:
            logger.warning(f"Vector indexing failed: {exc}")
            yield {"type": "agent_warning", "agent": "document_indexing", "message": str(exc)}

        # Phase 2: Validation first (required for subsequent agents)
        yield {"type": "agent_start", "agent": "validation", "message": "Validating document checklist…"}
        validation_result = await self.validation_agent.evaluate(
            required_documents=criteria.get("required_documents", []),
            bidder_documents=bidder.get("documents", []),
        )
        yield {
            "type": "agent_complete",
            "agent": "validation",
            "status": validation_result.get("status"),
            "confidence": validation_result.get("confidence"),
        }

        # Phase 3: Run Finance, Tech, Compliance, Fraud in parallel
        yield {"type": "agent_start", "agent": "parallel_eval", "message": "Running parallel agent evaluation…"}

        async def run_with_timeout(task_coro, agent_name):
            try:
                return await asyncio.wait_for(task_coro, timeout=120)
            except asyncio.TimeoutError:
                logger.error(f"Agent {agent_name} timed out after 120s")
                return {"status": "needs_review", "confidence": 0.0, "agent_reasoning": f"Timeout error in {agent_name}", "red_flags": ["Agent Timeout"]}
            except Exception as e:
                logger.error(f"Agent {agent_name} failed: {e}")
                return {"status": "needs_review", "confidence": 0.0, "agent_reasoning": f"Error in {agent_name}: {e}", "red_flags": ["Agent Error"]}

        finance_task = run_with_timeout(
            self.finance_agent.evaluate(
                criteria=criteria.get("financial", []),
                bidder_data=bidder,
                vector_store=self.vector_store,
            ), "finance"
        )
        tech_task = run_with_timeout(
            self.tech_agent.evaluate(
                criteria=criteria.get("technical", []),
                bidder_data=bidder,
                vector_store=self.vector_store,
            ), "tech"
        )
        compliance_task = run_with_timeout(
            self.compliance_agent.evaluate(
                criteria=criteria.get("compliance", []),
                bidder_data=bidder,
                vector_store=self.vector_store,
            ), "compliance"
        )
        fraud_task = run_with_timeout(
            self.fraud_agent.evaluate(
                bidder_data=bidder,
                documents=bidder.get("documents", []),
                vector_store=self.vector_store,
            ), "fraud"
        )

        finance_result, tech_result, compliance_result, fraud_result = await asyncio.gather(
            finance_task, tech_task, compliance_task, fraud_task
        )

        for agent, result in [
            ("finance", finance_result),
            ("tech", tech_result),
            ("compliance", compliance_result),
            ("fraud", fraud_result),
        ]:
            yield {
                "type": "agent_complete",
                "agent": agent,
                "status": result.get("status"),
                "confidence": result.get("confidence"),
            }

        # Phase 4: Synthesis
        yield {"type": "agent_start", "agent": "synthesize", "message": "Synthesizing final verdict…"}

        final = await self._synthesize(
            criteria=criteria,
            finance=finance_result,
            tech=tech_result,
            compliance=compliance_result,
            validation=validation_result,
            fraud=fraud_result,
        )

        # Phase 5: Save to DB
        evaluation_id = await self._save_evaluation(
            tender_id=str(tender.get("id")),
            bidder_id=str(bidder.get("id")),
            finance=finance_result,
            tech=tech_result,
            compliance=compliance_result,
            validation=validation_result,
            fraud=fraud_result,
            final=final,
        )

        # Audit
        await self.audit_logger.log_evaluation(
            evaluation_id=evaluation_id,
            state={
                "final_verdict": final.get("final_verdict"),
                "confidence_score": final.get("confidence_score"),
            },
            execution_time_ms=(time.time() - start_ts) * 1000,
        )

        yield {
            "type": "evaluation_complete",
            "evaluation_id": evaluation_id,
            "verdict": final.get("final_verdict"),
            "confidence": final.get("confidence_score"),
            "needs_review": final.get("needs_review", False),
        }

        # Phase 6: Send email notification to bidder (non-blocking)
        bidder_email = bidder.get("email", "")
        if bidder_email:
            asyncio.create_task(
                send_evaluation_result(
                    bidder_email=bidder_email,
                    company_name=bidder.get("company_name", "Bidder"),
                    tender_title=tender.get("title", "Government Tender"),
                    tender_number=tender.get("tender_number", ""),
                    verdict=final.get("final_verdict", "needs_review"),
                    confidence=final.get("confidence_score", 0.0),
                    evaluation_id=evaluation_id,
                    finance=finance_result,
                    tech=tech_result,
                    compliance=compliance_result,
                    validation=validation_result,
                    fraud=fraud_result,
                    explanation=final.get("explanation_chain", {}),
                )
            )
            yield {"type": "email_queued", "message": f"Evaluation result email queued for {bidder_email}"}

    async def _synthesize(
        self,
        criteria: dict,
        finance: dict,
        tech: dict,
        compliance: dict,
        validation: dict,
        fraud: dict,
    ) -> Dict[str, Any]:
        prompt = SYNTHESIS_PROMPT.format(
            criteria=json.dumps(criteria, indent=2)[:2000],
            finance_status=finance.get("status"),
            finance_conf=finance.get("confidence"),
            finance_reasoning=finance.get("agent_reasoning", "")[:300],
            finance_flags=json.dumps(finance.get("red_flags", [])),
            tech_status=tech.get("status"),
            tech_conf=tech.get("confidence"),
            tech_reasoning=tech.get("agent_reasoning", "")[:300],
            compliance_status=compliance.get("status"),
            compliance_conf=compliance.get("confidence"),
            compliance_reasoning=compliance.get("agent_reasoning", "")[:300],
            gst_status=compliance.get("gst_status", "N/A"),
            validation_status=validation.get("status"),
            validation_conf=validation.get("confidence"),
            missing_docs=json.dumps(validation.get("missing_documents", [])),
            fraud_status=fraud.get("status"),
            fraud_risk=fraud.get("risk_score", 0),
            fraud_indicators=json.dumps(
                [i.get("type") for i in fraud.get("fraud_indicators", [])]
            ),
        )

        try:
            resp = await self.llm.ainvoke(prompt)
            content = resp.content if hasattr(resp, "content") else str(resp)
            text = re.sub(r"```json\s*", "", content)
            text = re.sub(r"```\s*", "", text)
            return json.loads(text.strip())
        except Exception as exc:
            logger.error(f"Synthesis failed: {exc}")
            # Apply deterministic fallback rules
            return self._deterministic_synthesis(finance, tech, compliance, validation, fraud)

    def _deterministic_synthesis(self, finance, tech, compliance, validation, fraud) -> dict:
        """Pure rule-based fallback — no LLM needed."""
        statuses = [
            finance.get("status"), tech.get("status"),
            compliance.get("status"), validation.get("status"),
        ]
        fraud_risk = fraud.get("risk_score", 0)

        if "fail" in statuses or fraud_risk > 70:
            verdict = "not_eligible"
        elif "needs_review" in statuses or fraud_risk > 40:
            verdict = "needs_review"
        else:
            verdict = "eligible"

        confs = [
            finance.get("confidence", 0) * 0.30,
            tech.get("confidence", 0) * 0.30,
            compliance.get("confidence", 0) * 0.20,
            validation.get("confidence", 0) * 0.10,
            (1 - fraud_risk / 100) * 0.10,
        ]
        confidence = sum(confs)

        return {
            "final_verdict": verdict,
            "confidence_score": round(confidence, 3),
            "explanation_chain": {
                "summary": f"Deterministic rule-based verdict: {verdict}",
                "criterion_analysis": [],
                "risk_factors": fraud.get("red_flags", []),
                "recommendation": "Review individual agent results for details.",
            },
            "needs_review": verdict == "needs_review" or confidence < 0.75,
            "review_reason": "Low confidence or conflicting signals" if confidence < 0.75 else "",
        }

    async def _save_evaluation(
        self,
        tender_id: str,
        bidder_id: str,
        finance: dict,
        tech: dict,
        compliance: dict,
        validation: dict,
        fraud: dict,
        final: dict,
    ) -> str:
        record = {
            "tender_id": tender_id,
            "bidder_id": bidder_id,
            "final_verdict": final.get("final_verdict"),
            "confidence_score": final.get("confidence_score"),
            "finance_verdict": finance,
            "tech_verdict": tech,
            "compliance_verdict": compliance,
            "validation_verdict": validation,
            "fraud_verdict": fraud,
            "explanation_chain": final.get("explanation_chain"),
            "needs_human_review": final.get("needs_review", False),
            "review_reason": final.get("review_reason", ""),
        }
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: get_supabase()
                .table("evaluations")
                .upsert(record, on_conflict="tender_id,bidder_id")
                .execute(),
            )
            evaluation_id = result.data[0]["id"]

            # Mark bidder as evaluated so it doesn't re-trigger
            bidder_status = "escalated" if final.get("needs_review") else "completed"
            await loop.run_in_executor(
                None,
                lambda: get_supabase()
                .table("bidders")
                .update({"evaluation_status": bidder_status})
                .eq("id", bidder_id)
                .execute(),
            )
            return evaluation_id
        except Exception as exc:
            logger.error(f"Failed to save evaluation: {exc}")
            return "save-error"
