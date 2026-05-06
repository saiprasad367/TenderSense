"""
Evaluation Service — result retrieval, review queue, analytics, PDF export.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from database.supabase_client import get_supabase
from utils.audit_logger import AuditLogger
from utils.pdf_generator import generate_evaluation_report

logger = logging.getLogger("tendersense.evaluation_service")
audit = AuditLogger()


class EvaluationService:
    async def get_results(
        self,
        tender_id: str,
        verdict_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        sb = get_supabase()
        q = (
            sb.table("evaluations")
            .select("*, bidders(company_name, gstin, bid_amount)")
            .eq("tender_id", tender_id)
            .order("confidence_score", desc=True)
        )
        if verdict_filter:
            q = q.eq("final_verdict", verdict_filter)

        res = await asyncio.get_event_loop().run_in_executor(None, lambda: q.execute())
        rows = res.data or []

        # Flatten bidder data for frontend shape
        for row in rows:
            bidder_info = row.pop("bidders", {}) or {}
            row["bidder_name"] = bidder_info.get("company_name", "")
            row["bidder_gstin"] = bidder_info.get("gstin", "")
            row["bid_amount"] = bidder_info.get("bid_amount")
        return rows

    async def get_pending_bidders(
        self, tender_id: str, bidder_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Return bidders with completed OCR that haven't been evaluated yet."""
        sb = get_supabase()
        q = (
            sb.table("bidders")
            .select("*")
            .eq("tender_id", tender_id)
            .in_("evaluation_status", ["pending", "in_progress"])
        )
        if bidder_ids:
            q = q.in_("id", bidder_ids)

        res = await asyncio.get_event_loop().run_in_executor(None, lambda: q.execute())
        return res.data or []

    async def get_review_queue(self, department: Optional[str] = None) -> List[Dict[str, Any]]:
        sb = get_supabase()
        q = (
            sb.table("evaluations")
            .select("*, bidders(company_name, gstin, bid_amount), tenders(title, department)")
            .eq("needs_human_review", True)
            .is_("human_verdict", "null")
            .order("evaluated_at", desc=True)
        )
        if department:
            # Filter via join — post-process
            res = await asyncio.get_event_loop().run_in_executor(None, lambda: q.execute())
            rows = [
                r for r in (res.data or [])
                if (r.get("tenders") or {}).get("department") == department
            ]
        else:
            res = await asyncio.get_event_loop().run_in_executor(None, lambda: q.execute())
            rows = res.data or []

        for row in rows:
            bidder = row.pop("bidders", {}) or {}
            tender = row.pop("tenders", {}) or {}
            row["bidder_name"] = bidder.get("company_name", "")
            row["bidder_gstin"] = bidder.get("gstin", "")
            row["bid_amount"] = bidder.get("bid_amount")
            row["tender_title"] = tender.get("title", "")
            row["department"] = tender.get("department", "")
        return rows

    async def submit_review(
        self,
        evaluation_id: str,
        verdict: str,
        notes: str,
        reviewer_id: str,
        reviewer_email: str = "",
        reviewer_role: str = "",
    ) -> None:
        sb = get_supabase()

        old_res = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: sb.table("evaluations").select("final_verdict").eq("id", evaluation_id).single().execute(),
        )
        old_verdict = (old_res.data or {}).get("final_verdict")

        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: sb.table("evaluations").update({
                "human_verdict": verdict,
                "human_notes": notes,
                "reviewed_by": reviewer_id,
                "reviewed_at": "now()",
            }).eq("id", evaluation_id).execute(),
        )

        bidder_id = (old_res.data or {}).get("bidder_id")
        if bidder_id:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: sb.table("bidders").update({
                    "evaluation_status": "completed"
                }).eq("id", bidder_id).execute(),
            )

        await audit.log(
            entity_type="evaluation",
            entity_id=evaluation_id,
            action="HUMAN_REVIEW",
            user_id=reviewer_id,
            user_email=reviewer_email,
            user_role=reviewer_role,
            old_value={"ai_verdict": old_verdict},
            new_value={"human_verdict": verdict, "notes": notes},
        )

    async def get_explanation_chain(self, evaluation_id: str) -> Dict[str, Any]:
        sb = get_supabase()
        res = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: sb.table("evaluations")
            .select("explanation_chain, finance_verdict, tech_verdict, compliance_verdict, validation_verdict, fraud_verdict, final_verdict, confidence_score")
            .eq("id", evaluation_id)
            .single()
            .execute(),
        )
        return res.data or {}

    async def get_analytics(self, department: Optional[str] = None) -> Dict[str, Any]:
        sb = get_supabase()

        # Tenders count
        tq = sb.table("tenders").select("id, status, created_at", count="exact")
        if department:
            tq = tq.eq("department", department)
        t_res = await asyncio.get_event_loop().run_in_executor(None, lambda: tq.execute())
        tenders = t_res.data or []

        # Evaluations breakdown
        eq_ = sb.table("evaluations").select("id, final_verdict, confidence_score, needs_human_review, evaluated_at, bidders(company_name, gstin), tenders(id, tender_number)")
        e_res = await asyncio.get_event_loop().run_in_executor(None, lambda: eq_.execute())
        evals = e_res.data or []

        eligible = sum(1 for e in evals if e.get("final_verdict") == "eligible")
        not_elig = sum(1 for e in evals if e.get("final_verdict") == "not_eligible")
        review = sum(1 for e in evals if e.get("final_verdict") == "needs_review")
        avg_conf = (
            sum(e.get("confidence_score", 0) for e in evals) / len(evals)
            if evals else 0.0
        )

        # Flatten for frontend
        recent = sorted(evals, key=lambda x: x.get("evaluated_at", ""), reverse=True)[:10]
        for r in recent:
            bidder = r.pop("bidders", {}) or {}
            tender = r.pop("tenders", {}) or {}
            r["bidder_name"] = bidder.get("company_name", "")
            r["tender_title"] = tender.get("tender_number", "")

        return {
            "tenders_processed": len(tenders),
            "bidders_evaluated": len(evals),
            "eligible": eligible,
            "not_eligible": not_elig,
            "needs_review": review,
            "avg_confidence": round(avg_conf, 3),
            "active_tenders": sum(1 for t in tenders if t.get("status") == "active"),
            "recent_evaluations": recent,
        }

    async def generate_report(self, tender_id: str) -> bytes:
        from services.tender_service import TenderService
        ts = TenderService()
        tender = await ts.get_by_id(tender_id)
        if not tender:
            raise ValueError(f"Tender {tender_id} not found")

        evaluations = await self.get_results(tender_id)

        loop = asyncio.get_event_loop()
        pdf_bytes = await loop.run_in_executor(
            None, generate_evaluation_report, tender, evaluations
        )
        return pdf_bytes
