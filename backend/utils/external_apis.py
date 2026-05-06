"""
External Government API clients — GST portal + MCA.
Graceful degradation: if API key absent or timeout, returns a "needs_manual_verification" flag.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("tendersense.external_apis")

GST_BASE = os.getenv("GST_API_BASE_URL", "https://api.gst.gov.in")
GST_KEY = os.getenv("GST_API_KEY", "")
MCA_BASE = os.getenv("MCA_API_BASE_URL", "https://www.mca.gov.in")
MCA_KEY = os.getenv("MCA_API_KEY", "")

TIMEOUT = 10.0  # seconds


async def verify_gstin(gstin: str) -> Dict[str, Any]:
    """
    Verify GSTIN via GST portal.
    Returns: {valid, active, taxpayer_type, state, defaults_last_3yr, raw}
    """
    if not GST_KEY:
        logger.warning(f"GST_API_KEY not set — skipping live GSTIN verification for {gstin}")
        return _degraded("gstin", gstin, "API key not configured")

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                f"{GST_BASE}/commonapi/v1.1/search",
                params={"action": "TP", "gstin": gstin},
                headers={"Authorization": f"Bearer {GST_KEY}"},
            )
            resp.raise_for_status()
            data = resp.json()

            sts = data.get("sts", "").lower()
            return {
                "valid": True,
                "active": sts == "active",
                "taxpayer_type": data.get("dty", "unknown"),
                "state": data.get("stj", ""),
                "defaults_last_3yr": int(data.get("isFieldVisit", 0)),
                "needs_manual_verification": False,
                "raw": data,
            }
    except Exception as exc:
        logger.warning(f"GST API error for {gstin}: {exc}")
        return _degraded("gstin", gstin, str(exc))


async def verify_pan(pan: str, name: str) -> Dict[str, Any]:
    """
    Verify PAN and name match via Income Tax API (placeholder endpoint).
    """
    if not GST_KEY:
        return _degraded("pan", pan, "API key not configured")

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{GST_BASE}/commonapi/v1.0/pan-verify",
                json={"pan": pan, "name": name},
                headers={"Authorization": f"Bearer {GST_KEY}"},
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "valid": data.get("valid", False),
                "name_match": data.get("nameMatch", False),
                "status": data.get("status", "unknown"),
                "needs_manual_verification": False,
                "raw": data,
            }
    except Exception as exc:
        logger.warning(f"PAN verify error for {pan}: {exc}")
        return _degraded("pan", pan, str(exc))


async def lookup_mca_company(cin: str) -> Dict[str, Any]:
    """
    Look up company details from MCA21 portal.
    """
    if not MCA_KEY:
        return _degraded("cin", cin, "MCA API key not configured")

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                f"{MCA_BASE}/api/company/{cin}",
                headers={"Authorization": f"Bearer {MCA_KEY}"},
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "found": True,
                "company_name": data.get("companyName", ""),
                "registered_address": data.get("registeredAddress", ""),
                "status": data.get("companyStatus", "unknown"),
                "paid_up_capital": data.get("paidUpCapital", 0),
                "authorized_capital": data.get("authorizedCapital", 0),
                "needs_manual_verification": False,
                "raw": data,
            }
    except Exception as exc:
        logger.warning(f"MCA lookup error for {cin}: {exc}")
        return _degraded("cin", cin, str(exc))


def _degraded(field: str, value: str, reason: str) -> Dict[str, Any]:
    return {
        "valid": None,
        "needs_manual_verification": True,
        "degradation_reason": reason,
        field: value,
    }
