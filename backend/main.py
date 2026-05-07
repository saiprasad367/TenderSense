"""
TenderSense AI Backend — Main FastAPI Application
Production-grade multi-agent tender evaluation system for Karnataka Gov deployment.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Optional

import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_OFF"] = "True"

# Monkey-patch posthog to prevent telemetry errors in older ChromaDB versions
try:
    import posthog
    posthog.capture = lambda *args, **kwargs: None
except ImportError:
    pass

from dotenv import load_dotenv
load_dotenv()

import uvicorn
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse
from pydantic_settings import BaseSettings, SettingsConfigDict

# ── local imports ──────────────────────────────────────────────────────────────
from auth.supabase_auth import verify_token, check_permission, UserContext
from database.supabase_client import get_supabase
from routers import tenders, bidders, evaluations, review, audit, reports, analytics, auth

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("tendersense.main")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-sonnet-4"
    chroma_persist_dir: str = "./chroma_db"
    frontend_url: str = "http://localhost:5173"
    app_env: str = "development"
    max_file_size_mb: int = 50


settings = Settings()


# ── lifespan ───────────────────────────────────────────────────────────────────
async def warmup_vector_store():
    """Warm up ChromaDB in the background to avoid blocking port binding."""
    try:
        from utils.vector_store import VectorStore
        vs = VectorStore()
        await vs.health_check()
        logger.info("✅ ChromaDB ready")
    except Exception as e:
        logger.warning(f"⚠️  ChromaDB warmup failed: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 TenderSense AI backend starting up …")
    # Background warmup disabled for troubleshooting
    yield
    logger.info("🛑 TenderSense AI backend shutting down")


# ── app factory ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="TenderSense AI",
    version="1.0.0",
    description="Multi-agent government tender evaluation system",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── routers ───────────────────────────────────────────────────────────────────
app.include_router(tenders.router, prefix="/api/tenders", tags=["Tenders"])
app.include_router(bidders.router, prefix="/api/bidders", tags=["Bidders"])
app.include_router(evaluations.router, prefix="/api/evaluations", tags=["Evaluations"])
app.include_router(review.router, prefix="/api/review", tags=["Review"])
app.include_router(audit.router, prefix="/api/audit", tags=["Audit"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])


@app.get("/")
async def root():
    return {"status": "TenderSense AI Backend is Live", "version": "1.0.0"}


# ── health ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """System health check — verifies all subsystems."""
    checks: dict[str, str] = {}

    # Database
    try:
        sb = get_supabase()
        sb.table("tenders").select("id").limit(1).execute()
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # ChromaDB
    try:
        from utils.vector_store import VectorStore
        await VectorStore().health_check()
        checks["vector_store"] = "ok"
    except Exception as e:
        checks["vector_store"] = f"error: {e}"

    # OpenRouter
    try:
        checks["llm"] = "ok" if settings.openrouter_api_key else "no_key"
    except Exception as e:
        checks["llm"] = f"error: {e}"

    overall = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "version": "1.0.0", "services": checks}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_env == "development",
        log_level="info",
    )
