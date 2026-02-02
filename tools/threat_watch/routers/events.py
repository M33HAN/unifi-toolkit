"""
API routes for threat events
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from datetime import datetime, timezone, timedelta
from typing import Optional

from shared.database import get_db_session
from tools.threat_watch.database import ThreatEvent

logger = logging.getLogger(__name__)
from tools.threat_watch.models import (
    ThreatEventResponse,
    ThreatEventDetail,
    ThreatEventsListResponse,
    ThreatStatsResponse,
    ThreatTimelineResponse,
    SeverityCount,
    CategoryCount,
    CountryCount,
    TopAttacker,
    TimelinePoint
)

router = APIRouter(prefix="/api/events", tags=["events"])

SEVERITY_LABELS = {
    1: "High",
    2: "Medium",
    3: "Low"
}


@router.get("", response_model=ThreatEventsListResponse)
async def get_events(
    start_time: Optional[datetime] = Query(None, description="Filter events after this time"),
    end_time: Optional[datetime] = Query(None, description="Filter events before this time"),
    severity: Optional[int] = Query(None, ge=1, le=3, description="Filter by severity (1=high, 2=medium, 3=low)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    action: Optional[str] = Query(None, description="Filter by action (alert, block)"),
    src_ip: Optional[str] = Query(None, description="Filter by source IP"),
    dest_ip: Optional[str] = Query(None, description="Filter by destination IP"),
    search: Optional[str] = Query(None, description="Search in signature/message"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Events per page"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get paginated list of threat events with optional filtering
    """
    # Build query
    query = select(ThreatEvent)
    count_query = select(func.count(ThreatEvent.id))

    # Apply filters
    filters = []

    if start_time:
        filters.append(ThreatEvent.timestamp >= start_time)
    if end_time:
        filters.append(ThreatEvent.timestamp <= end_time)
    if severity:
        filters.append(ThreatEvent.severity == severity)
    if category:
        filters.append(ThreatEvent.category == category)
    if action:
        filters.append(ThreatEvent.action == action)
    if src_ip:
        filters.append(ThreatEvent.src_ip == src_ip)
    if dest_ip:
        filters.append(ThreatEvent.dest_ip == dest_ip)
    if search:
        search_filter = or_(
            ThreatEvent.signature.ilike(f"%{search}%"),
            ThreatEvent.message.ilike(f"%{search}%")
        )
        filters.append(search_filter)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination and ordering
    offset = (page - 1) * page_size
    query = query.order_by(desc(ThreatEvent.timestamp)).offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    events = result.scalars().all()

    has_more = (offset + len(events)) < total

    return ThreatEventsListResponse(
        events=[ThreatEventResponse.model_validate(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more
    )


@router.get("/stats", response_model=ThreatStatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get threat statistics overview
    """
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    # Total events
    total_result = await db.execute(select(func.count(ThreatEvent.id)))
    total_events = total_result.scalar() or 0

    # Events in last 24 hours
    result_24h = await db.execute(
        select(func.count(ThreatEvent.id)).where(ThreatEvent.timestamp >= day_ago)
    )
    events_24h = result_24h.scalar() or 0

    # Events in last 7 days
    result_7d = await db.execute(
        select(func.count(ThreatEvent.id)).where(ThreatEvent.timestamp >= week_ago)
    )
    events_7d = result_7d.scalar() or 0

    # Blocked vs Alert counts
    blocked_result = await db.execute(
        select(func.count(ThreatEvent.id)).where(ThreatEvent.action == "block")
    )
    blocked_count = blocked_result.scalar() or 0

    alert_result = await db.execute(
        select(func.count(ThreatEvent.id)).where(ThreatEvent.action == "alert")
    )
    alert_count = alert_result.scalar() or 0

    # By severity
    severity_result = await db.execute(
        select(ThreatEvent.severity, func.count(ThreatEvent.id))
        .where(ThreatEvent.severity.isnot(None))
        .group_by(ThreatEvent.severity)
        .order_by(ThreatEvent.severity)
    )
    by_severity = [
        SeverityCount(
            severity=sev,
            label=SEVERITY_LABELS.get(sev, f"Severity {sev}"),
            count=count
        )
        for sev, count in severity_result.all()
    ]

    # By category (top 10)
    category_result = await db.execute(
        select(ThreatEvent.category, func.count(ThreatEvent.id))
        .where(ThreatEvent.category.isnot(None))
        .group_by(ThreatEvent.category)
        .order_by(desc(func.count(ThreatEvent.id)))
        .limit(10)
    )
    by_category = [
        CategoryCount(category=cat or "Unknown", count=count)
        for cat, count in category_result.all()
    ]

    # By source country (top 10)
    country_result = await db.execute(
        select(ThreatEvent.src_country, func.count(ThreatEvent.id))
        .where(ThreatEvent.src_country.isnot(None))
        .group_by(ThreatEvent.src_country)
        .order_by(desc(func.count(ThreatEvent.id)))
        .limit(10)
    )
    by_country = [
        CountryCount(country=country or "Unknown", country_code=country, count=count)
        for country, count in country_result.all()
    ]

    # Top attackers (top 10 source IPs)
    attackers_result = await db.execute(
        select(
            ThreatEvent.src_ip,
            func.count(ThreatEvent.id).label('count'),
            func.max(ThreatEvent.src_country).label('country'),
            func.max(ThreatEvent.src_org).label('org'),
            func.max(ThreatEvent.timestamp).label('last_seen')
        )
        .where(ThreatEvent.src_ip.isnot(None))
        .group_by(ThreatEvent.src_ip)
        .order_by(desc(func.count(ThreatEvent.id)))
        .limit(10)
    )
    top_attackers = [
        TopAttacker(
            ip=row.src_ip,
            count=row.count,
            country=row.country,
            org=row.org,
            last_seen=row.last_seen
        )
        for row in attackers_result.all()
    ]

    return ThreatStatsResponse(
        total_events=total_events,
        events_24h=events_24h,
        events_7d=events_7d,
        blocked_count=blocked_count,
        alert_count=alert_count,
        by_severity=by_severity,
        by_category=by_category,
        by_country=by_country,
        top_attackers=top_attackers
    )


@router.get("/timeline", response_model=ThreatTimelineResponse)
async def get_timeline(
    interval: str = Query("hour", regex="^(hour|day)$", description="Time interval (hour or day)"),
    days: int = Query(7, ge=1, le=30, description="Number of days to include"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get threat event counts over time for charting
    """
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(days=days)

    # Get all events in range
    result = await db.execute(
        select(ThreatEvent.timestamp)
        .where(ThreatEvent.timestamp >= start_time)
        .order_by(ThreatEvent.timestamp)
    )
    timestamps = [row[0] for row in result.all()]

    # Bucket by interval
    buckets = {}
    for ts in timestamps:
        if interval == "hour":
            bucket = ts.replace(minute=0, second=0, microsecond=0)
        else:  # day
            bucket = ts.replace(hour=0, minute=0, second=0, microsecond=0)

        if bucket not in buckets:
            buckets[bucket] = 0
        buckets[bucket] += 1

    # Convert to list sorted by time
    data = [
        TimelinePoint(timestamp=ts, count=count)
        for ts, count in sorted(buckets.items())
    ]

    return ThreatTimelineResponse(interval=interval, data=data)


@router.get("/categories")
async def get_categories(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get list of all threat categories
    """
    result = await db.execute(
        select(ThreatEvent.category)
        .where(ThreatEvent.category.isnot(None))
        .distinct()
        .order_by(ThreatEvent.category)
    )
    categories = [row[0] for row in result.all()]
    return {"categories": categories}


@router.get("/{event_id}", response_model=ThreatEventDetail)
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get detailed information for a single threat event
    """
    result = await db.execute(
        select(ThreatEvent).where(ThreatEvent.id == event_id)
    )
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return ThreatEventDetail.model_validate(event)


@router.get("/ip/{ip_address}")
async def get_events_by_ip(
    ip_address: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get all events for a specific IP address (source or destination)
    """
    # Build query for events where IP is source or destination
    query = select(ThreatEvent).where(
        or_(
            ThreatEvent.src_ip == ip_address,
            ThreatEvent.dest_ip == ip_address
        )
    )
    count_query = select(func.count(ThreatEvent.id)).where(
        or_(
            ThreatEvent.src_ip == ip_address,
            ThreatEvent.dest_ip == ip_address
        )
    )

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination and ordering
    offset = (page - 1) * page_size
    query = query.order_by(desc(ThreatEvent.timestamp)).offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    events = result.scalars().all()

    has_more = (offset + len(events)) < total

    return ThreatEventsListResponse(
        events=[ThreatEventResponse.model_validate(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more
    )


@router.get("/debug/test-fetch")
async def debug_test_fetch(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Debug endpoint to test IPS event fetching from UniFi.

    This endpoint connects to UniFi, attempts to fetch IPS events using both
    the v2 traffic-flows API (Network 10.x+) and legacy stat/ips/event API,
    and returns diagnostic information about the responses.
    """
    from shared.models.unifi_config import UniFiConfig
    from shared.unifi_client import UniFiClient
    from shared.crypto import decrypt_password, decrypt_api_key
    import time

    # Get UniFi config
    result = await db.execute(select(UniFiConfig).where(UniFiConfig.id == 1))
    unifi_config = result.scalar_one_or_none()

    if not unifi_config:
        return {
            "success": False,
            "error": "No UniFi configuration found",
            "hint": "Configure UniFi controller in dashboard settings"
        }

    # Decrypt credentials
    password = None
    api_key = None
    try:
        if unifi_config.password_encrypted:
            password = decrypt_password(unifi_config.password_encrypted)
        if unifi_config.api_key_encrypted:
            api_key = decrypt_api_key(unifi_config.api_key_encrypted)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to decrypt credentials: {str(e)}"
        }

    # Create client
    client = UniFiClient(
        host=unifi_config.controller_url,
        username=unifi_config.username,
        password=password,
        api_key=api_key,
        site=unifi_config.site_id,
        verify_ssl=unifi_config.verify_ssl
    )

    try:
        # Connect
        connected = await client.connect()
        if not connected:
            return {
                "success": False,
                "error": "Failed to connect to UniFi controller",
                "controller_url": unifi_config.controller_url,
                "site": unifi_config.site_id
            }

        # Get gateway info
        gateway_info = await client.get_gateway_info()
        ips_settings = await client.get_ips_settings()

        # Calculate time range (last 24 hours)
        now_ms = int(time.time() * 1000)
        day_ago_ms = now_ms - (24 * 60 * 60 * 1000)

        # Test both APIs separately for diagnostics
        v2_events = []
        legacy_events = []
        v2_error = None
        legacy_error = None

        # Test v2 traffic-flows API (Network 10.x+)
        if client.is_unifi_os:
            try:
                v2_events = await client.get_traffic_flows(limit=10, time_range="24h")
            except Exception as e:
                v2_error = str(e)

        # Test legacy stat/ips/event API
        try:
            if client.is_unifi_os:
                url = f"{client.host}/proxy/network/api/s/{client.site}/stat/ips/event"
            else:
                url = f"{client.host}/api/s/{client.site}/stat/ips/event"

            payload = {
                "start": day_ago_ms,
                "end": now_ms,
                "_limit": 10
            }

            async with client._session.post(url, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    legacy_events = data.get('data', [])
                else:
                    legacy_error = f"HTTP {resp.status}"
        except Exception as e:
            legacy_error = str(e)

        # Determine which API is working
        working_api = None
        if v2_events:
            working_api = "v2_traffic_flows"
        elif legacy_events:
            working_api = "legacy_stat_ips_event"

        # Build diagnostic response
        response = {
            "success": True,
            "connection": {
                "controller_url": unifi_config.controller_url,
                "site": unifi_config.site_id,
                "is_unifi_os": client.is_unifi_os,
                "detected_type": client._detected_type
            },
            "gateway": gateway_info,
            "ips_settings": ips_settings,
            "api_tests": {
                "v2_traffic_flows": {
                    "available": client.is_unifi_os,
                    "events_returned": len(v2_events),
                    "error": v2_error,
                    "sample_event_keys": list(v2_events[0].keys()) if v2_events else None,
                    "sample_event": v2_events[0] if v2_events else None,
                    "endpoint": "/proxy/network/v2/api/site/{site}/traffic-flows"
                },
                "legacy_stat_ips_event": {
                    "available": True,
                    "events_returned": len(legacy_events),
                    "error": legacy_error,
                    "sample_event_keys": list(legacy_events[0].keys()) if legacy_events else None,
                    "sample_event": legacy_events[0] if legacy_events else None,
                    "endpoint": "/proxy/network/api/s/{site}/stat/ips/event"
                }
            },
            "working_api": working_api,
            "total_events": len(v2_events) + len(legacy_events)
        }

        # Check for common issues
        issues = []
        if not gateway_info.get("has_gateway"):
            issues.append("No gateway device found")
        if not gateway_info.get("supports_ids_ips"):
            issues.append(f"Gateway ({gateway_info.get('gateway_name')}) does not support IDS/IPS")
        if ips_settings and not ips_settings.get("ips_enabled"):
            issues.append(f"IDS/IPS is disabled (mode: {ips_settings.get('ips_mode')})")
        if not client.is_unifi_os:
            issues.append("Legacy controller detected - v2 API not available")
        if len(v2_events) == 0 and len(legacy_events) == 0:
            issues.append("No events returned from either API - this may be normal if no threats detected in last 24 hours")
        if v2_events and not legacy_events:
            issues.append("Only v2 API returned events - using Network 10.x traffic-flows endpoint")
        if legacy_events and not v2_events and client.is_unifi_os:
            issues.append("Only legacy API returned events - v2 traffic-flows may not be available on this firmware")

        if issues:
            response["issues"] = issues

        return response

    except Exception as e:
        logger.exception("Debug test fetch failed")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
    finally:
        await client.disconnect()
