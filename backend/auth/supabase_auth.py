"""
Supabase Auth — JWT verification + Role-Based Access Control
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import wraps
from typing import Optional

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, create_client

# ── client ─────────────────────────────────────────────────────────────────────
SUPABASE_URL = ""
SUPABASE_SERVICE_KEY = ""

_supabase: Optional[Client] = None


from dotenv import load_dotenv

def get_auth_client() -> Client:
    global _supabase, SUPABASE_URL, SUPABASE_SERVICE_KEY
    if _supabase is None:
        load_dotenv(override=True)
        SUPABASE_URL = os.getenv("SUPABASE_URL", "")
        SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        _supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _supabase


# ── RBAC ───────────────────────────────────────────────────────────────────────
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "admin":               ["all"],
    "senior_officer":      ["upload", "evaluate", "review", "approve", "export", "view"],
    "evaluation_officer":  ["upload", "evaluate", "review", "export", "view"],
    "viewer":              ["view", "export", "upload"],
}


@dataclass
class UserContext:
    user_id: str
    email: str
    role: str
    department: str
    is_active: bool


security = HTTPBearer(auto_error=False)


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> UserContext:
    """Verify Supabase JWT and return UserContext."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="No authentication credentials provided")

    token = credentials.credentials
    try:
        sb = get_auth_client()
        resp = sb.auth.get_user(token)
        if not resp or not resp.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        uid = resp.user.id
        user_data = (
            sb.table("users").select("*").eq("id", uid).execute()
        )
        
        row = user_data.data[0] if user_data.data else None
        
        if not row:
            # FALLBACK: Use metadata from the JWT if the profile hasn't synced to public.users yet
            metadata = resp.user.user_metadata or {}
            return UserContext(
                user_id=uid,
                email=resp.user.email or "",
                role=metadata.get("role", "viewer"),
                department=metadata.get("department", ""),
                is_active=True,
            )

        if not row.get("is_active", True):
            raise HTTPException(status_code=403, detail="User account is inactive")

        return UserContext(
            user_id=uid,
            email=resp.user.email or "",
            role=row.get("role", "viewer"),
            department=row.get("department", ""),
            is_active=row.get("is_active", True),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {exc}") from exc


def check_permission(required: str):
    """FastAPI dependency factory — raises 403 if role lacks permission."""

    async def _inner(user: UserContext = Security(verify_token)) -> UserContext:  # type: ignore[return]
        perms = ROLE_PERMISSIONS.get(user.role, [])
        if "all" in perms or required in perms:
            return user
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: '{required}' required. Your role: {user.role}",
        )

    return _inner
