"""
Immutable Audit Logger — writes to Supabase audit_logs table.
Designed to be append-only (RLS enforced on DB side).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from database.supabase_client import get_supabase

logger = logging.getLogger("tendersense.audit")


class AuditLogger:
    async def log(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        user_role: Optional[str] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        llm_prompt: Optional[str] = None,
        llm_response: Optional[str] = None,
        llm_model: Optional[str] = None,
        llm_tokens: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        record = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "user_id": user_id,
            "user_email": user_email,
            "user_role": user_role,
            "old_value": old_value,
            "new_value": new_value,
            "llm_prompt": llm_prompt[:8000] if llm_prompt else None,  # truncate
            "llm_response": llm_response[:8000] if llm_response else None,
            "llm_model": llm_model,
            "llm_tokens_used": llm_tokens,
            "ip_address": ip_address,
        }
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._sync_insert, record)
        except Exception as exc:
            logger.error(f"Audit log insert failed: {exc}")

    def _sync_insert(self, record: dict) -> None:
        sb = get_supabase()
        sb.table("audit_logs").insert(record).execute()

    async def log_evaluation(
        self,
        evaluation_id: str,
        state: dict,
        execution_time_ms: float,
    ) -> None:
        await self.log(
            entity_type="evaluation",
            entity_id=evaluation_id,
            action="AI_EVALUATION",
            new_value={
                "final_verdict": state.get("final_verdict"),
                "confidence_score": state.get("confidence_score"),
                "execution_time_ms": execution_time_ms,
            },
            llm_model="claude-sonnet-4",
        )
