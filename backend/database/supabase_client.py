"""
Supabase singleton client — use service-role key server-side only.
"""
from __future__ import annotations

import os
from typing import Optional

from supabase import Client, create_client

_client: Optional[Client] = None


from dotenv import load_dotenv

def get_supabase() -> Client:
    global _client
    if _client is None:
        load_dotenv(override=True)
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in environment")
        _client = create_client(url, key)
    return _client
