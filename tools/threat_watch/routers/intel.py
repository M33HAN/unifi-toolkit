"""
API routes for threat intelligence lookups (AbuseIPDB integration)
"""
import logging
import ipaddress
from datetime import datetime, timezone
from typing import Optional

import aiohttp
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from shared.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intel", tags=["intel"])

# AbuseIPDB category mapping
ABUSE_CATEGORIES = {
    1: "DNS Compromise",
    2: "DNS Poisoning",
    3: "Fraud Orders",
    4: "DDoS Attack",
    5: "FTP Brute-Force",
    6: "Ping of Death",
    7: "Phishing",
    8: "Fraud VoIP",
    9: "Open Proxy",
    10: "Web Spam",
    11: "Email Spam",
    12: "Blog Spam",
    13: "VPN IP",
    14: "Port Scan",
    15: "Hacking",
    16: "SQL Injection",
    17: "Spoofing",
    18: "Brute-Force",
    19: "Bad Web Bot",
    20: "Exploited Host",
    21: "Web App Attack",
    22: "SSH",
    23: "IoT Targeted",
}


class AbuseIPDBReport(BaseModel):
    """Individual abuse report"""
    reported_at: str
    comment: Optional[str] = None
    categories: list[str] = []
    reporter_country: Optional[str] = None


class ThreatIntelResponse(BaseModel):
    """Response model for threat intelligence lookup"""
    ip: str
    abuse_confidence_score: int
    is_public: bool
    is_whitelisted: Optional[bool] = None
    is_tor: bool
    country_code: Optional[str] = None
    country_name: Optional[str] = None
    usage_type: Optional[str] = None
    isp: Optional[str] = None
    domain: Optional[str] = None
    total_reports: int
    num_distinct_users: int
    last_reported_at: Optional[str] = None
    recent_reports: list[AbuseIPDBReport] = []
    risk_level: str  # "critical", "high", "medium", "low", "clean"
    risk_color: str  # hex color for UI


def _classify_risk(score: int) -> tuple[str, str]:
    """Classify risk level from AbuseIPDB confidence score"""
    if score >= 80:
        return "critical", "#ef4444"
    elif score >= 50:
        return "high", "#f97316"
    elif score >= 25:
        return "medium", "#f59e0b"
    elif score > 0:
        return "low", "#00e1ff"
    else:
        return "clean", "#10b981"


def _is_private_ip(ip_str: str) -> bool:
    """Check if an IP address is private/reserved"""
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_reserved or ip.is_loopback
    except ValueError:
        return False


@router.get("/check/{ip_address}", response_model=ThreatIntelResponse)
async def check_ip(
    ip_address: str,
    max_age_days: int = Query(90, ge=1, le=365, description="Max age of reports in days"),
):
    """
    Look up threat intelligence for an IP address via AbuseIPDB.
    
    Returns abuse confidence score, ISP, usage type, Tor detection,
    recent reports with categories, and a risk classification.
    
    Requires ABUSEIPDB_API_KEY to be set in environment.
    Free tier: 1000 checks/day.
    """
    settings = get_settings()

    if not settings.abuseipdb_api_key:
        raise HTTPException(
            status_code=503,
            detail="AbuseIPDB API key not configured. Set ABUSEIPDB_API_KEY in your .env file."
        )

    # Don't look up private IPs
    if _is_private_ip(ip_address):
        return ThreatIntelResponse(
            ip=ip_address,
            abuse_confidence_score=0,
            is_public=False,
            is_tor=False,
            total_reports=0,
            num_distinct_users=0,
            recent_reports=[],
            risk_level="clean",
            risk_color="#10b981",
            usage_type="Private/Reserved",
        )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.abuseipdb.com/api/v2/check",
                params={
                    "ipAddress": ip_address,
                    "maxAgeInDays": max_age_days,
                    "verbose": "",
                },
                headers={
                    "Key": settings.abuseipdb_api_key,
                    "Accept": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 401:
                    raise HTTPException(status_code=401, detail="Invalid AbuseIPDB API key")
                if resp.status == 429:
                    raise HTTPException(status_code=429, detail="AbuseIPDB rate limit exceeded (1000/day on free tier)")
                if resp.status != 200:
                    raise HTTPException(
                        status_code=502,
                        detail=f"AbuseIPDB returned HTTP {resp.status}"
                    )

                result = await resp.json()
                data = result.get("data", {})

    except aiohttp.ClientError as e:
        logger.error(f"AbuseIPDB request failed: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to reach AbuseIPDB: {str(e)}")

    # Parse reports
    recent_reports = []
    raw_reports = data.get("reports", [])[:10]  # Limit to 10 most recent
    for report in raw_reports:
        cat_ids = report.get("categories", [])
        cat_names = [ABUSE_CATEGORIES.get(c, f"Category {c}") for c in cat_ids]
        recent_reports.append(AbuseIPDBReport(
            reported_at=report.get("reportedAt", ""),
            comment=report.get("comment"),
            categories=cat_names,
            reporter_country=report.get("reporterCountryName"),
        ))

    score = data.get("abuseConfidenceScore", 0)
    risk_level, risk_color = _classify_risk(score)

    return ThreatIntelResponse(
        ip=ip_address,
        abuse_confidence_score=score,
        is_public=data.get("isPublic", True),
        is_whitelisted=data.get("isWhitelisted"),
        is_tor=data.get("isTor", False),
        country_code=data.get("countryCode"),
        country_name=data.get("countryName"),
        usage_type=data.get("usageType"),
        isp=data.get("isp"),
        domain=data.get("domain"),
        total_reports=data.get("totalReports", 0),
        num_distinct_users=data.get("numDistinctUsers", 0),
        last_reported_at=data.get("lastReportedAt"),
        recent_reports=recent_reports,
        risk_level=risk_level,
        risk_color=risk_color,
    )


@router.get("/status")
async def intel_status():
    """Check if threat intelligence is configured and available"""
    settings = get_settings()
    return {
        "abuseipdb_configured": settings.abuseipdb_api_key is not None,
        "provider": "AbuseIPDB" if settings.abuseipdb_api_key else None,
    }
