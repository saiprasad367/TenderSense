"""Pydantic models — Audit"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    action: str
    user_id: Optional[UUID]
    user_email: Optional[str]
    user_role: Optional[str]
    old_value: Optional[Dict[str, Any]]
    new_value: Optional[Dict[str, Any]]
    llm_model: Optional[str]
    llm_tokens_used: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
