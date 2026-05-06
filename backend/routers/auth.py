from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, EmailStr
from database.supabase_client import get_supabase
import logging

router = APIRouter()
logger = logging.getLogger("tendersense.auth")

class ProfileSync(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: str
    department: str = ""

@router.post("/sync")
async def sync_profile(profile: ProfileSync):
    """
    Sync Supabase Auth user to public.users table.
    Called by frontend after signup.
    """
    sb = get_supabase() # Uses service role to bypass RLS
    
    data = {
        "id": profile.id,
        "email": profile.email,
        "full_name": profile.full_name,
        "role": profile.role,
        "department": profile.department,
        "is_active": True
    }
    
    try:
        # Upsert user profile
        res = sb.table("users").upsert(data).execute()
        logger.info(f"Synced profile for user {profile.email}")
        return {"status": "success", "user": res.data[0] if res.data else None}
    except Exception as e:
        logger.error(f"Failed to sync profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sync profile: {e}")
