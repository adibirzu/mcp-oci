from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import os
import time
import json
import hashlib
import oci
from ..oci_client_adapter import OCIClients
from datetime import datetime, timezone
from oci.exceptions import ServiceError

_TTL = int(os.getenv("FINOPSAI_CACHE_TTL_SECONDS", "300"))
_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}

def _cache_key(tenancy_ocid: str, details: Dict[str, Any]) -> str:
    blob = json.dumps({"tenancy": tenancy_ocid, "details": details}, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()

def _parse_iso8601(ts: Any) -> Any:
    """
    Convert ISO8601 string with optional trailing 'Z' to timezone-aware datetime.
    If ts is already a datetime, return it unchanged.
    """
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        s = ts.strip()
        # Normalize 'Z' to '+00:00' for fromisoformat
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(s)
        except Exception:
            # Fallback: try naive parse and force UTC
            try:
                return datetime.fromisoformat(s.replace(" ", "T")).replace(tzinfo=timezone.utc)
            except Exception:
                pass
    return ts  # Let SDK try if parsing fails

def _to_midnight(dt: datetime, roll_to_next_if_not_midnight: bool = False) -> datetime:
    """
    Ensure datetime is exactly at 00:00:00.000000 UTC.
    If roll_to_next_if_not_midnight is True and the original datetime had any time component,
    return midnight of the next day (exclusive end bound expected by Usage API).
    """
    if not isinstance(dt, datetime):
        return dt
    # Force timezone to UTC if missing
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        # Normalize to UTC to avoid offset precision errors
        dt = dt.astimezone(timezone.utc)
    had_time = any([dt.hour, dt.minute, dt.second, dt.microsecond])
    base = dt.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    if roll_to_next_if_not_midnight and had_time:
        from datetime import timedelta
        return base + timedelta(days=1)
    return base

@dataclass
class UsageQuery:
    granularity: str  # DAILY | MONTHLY
    time_start: str
    time_end: str
    group_by: Optional[List[str]] = None
    group_by_tag: Optional[List[Dict[str, str]]] = None
    filter: Optional[Dict[str, Any]] = None
    forecast: bool = False
    compartment_depth: Optional[int] = None

def request_summarized_usages(clients: OCIClients, tenancy_ocid: str, q: UsageQuery) -> Dict[str, Any]:
    # Normalize time inputs to datetime objects (some regions strictly require datetimes)
    ts_start = _parse_iso8601(q.time_start)
    ts_end = _parse_iso8601(q.time_end)
    # Enforce Usage API precision: hours, minutes, seconds, fractions must be 0
    # Start: midnight of given date
    # End: midnight; if a time component was provided, roll to next day's midnight to create an exclusive bound
    ts_start = _to_midnight(ts_start, roll_to_next_if_not_midnight=False)
    ts_end = _to_midnight(ts_end, roll_to_next_if_not_midnight=True)

    # Create forecast object if requested: strict tenants require
    # time_forecast_started == time_usage_ended
    forecast_obj = None
    if q.forecast:
        forecast_obj = oci.usage_api.models.Forecast(
            forecast_type="BASIC",
            time_forecast_started=ts_end,
            time_forecast_ended=ts_end,
        )

    # Handle group_by vs group_by_tag conflict: group_by MUST be null when group_by_tag is present
    # Also avoid sending empty arrays; pass None instead to satisfy strict validators
    group_by_tag_param = q.group_by_tag if (q.group_by_tag and len(q.group_by_tag) > 0) else None
    group_by_param = None if group_by_tag_param else (q.group_by if (q.group_by and len(q.group_by) > 0) else None)

    # Ensure compartmentDepth is present when grouping by compartment
    cd = q.compartment_depth
    if cd is None and group_by_param:
        try:
            if any(str(g).lower().startswith("compartment") for g in group_by_param):
                cd = 7  # Usage API requires compartmentDepth <= 7
        except Exception:
            pass

    details = oci.usage_api.models.RequestSummarizedUsagesDetails(
        tenant_id=tenancy_ocid,
        granularity=(q.granularity or "DAILY").upper(),
        time_usage_started=ts_start,
        time_usage_ended=ts_end,
        query_type="COST",
        group_by=group_by_param,
        group_by_tag=group_by_tag_param,
        filter=q.filter,
        forecast=forecast_obj,
        compartment_depth=cd,
        is_aggregate_by_time=True,
    )
    # Create a hashable representation for caching
    details_dict = {
        'tenant_id': details.tenant_id,
        'time_usage_started': details.time_usage_started,
        'time_usage_ended': details.time_usage_ended,
        'granularity': details.granularity,
        'query_type': getattr(details, 'query_type', None),
        'group_by': getattr(details, 'group_by', None),
        'group_by_tag': getattr(details, 'group_by_tag', None),
        'compartment_depth': getattr(details, 'compartment_depth', None),
        'filter': str(getattr(details, 'filter', None)),
        'forecast': str(getattr(details, 'forecast', None)),
        'is_aggregate_by_time': getattr(details, 'is_aggregate_by_time', None)
    }
    key = _cache_key(tenancy_ocid, details_dict)
    now = time.time()
    if _TTL > 0 and key in _cache:
        exp, data = _cache[key]
        if now < exp:
            return data
        else:
            _cache.pop(key, None)

    # Simple retry/backoff loop to absorb Usage API 429s
    import random
    max_retries = int(os.getenv("FINOPSAI_USAGEAPI_MAX_RETRIES", "4"))
    base_delay = float(os.getenv("FINOPSAI_USAGEAPI_BACKOFF_SECONDS", "1.5"))
    attempt = 0
    while True:
        try:
            resp = clients.usage_api.request_summarized_usages(details)
            break
        except ServiceError as e:
            status = getattr(e, "status", None)
            code = str(getattr(e, "code", "") or "").lower()
            msg = str(getattr(e, "message", e) or "").lower()
            # Retry on 429 TooManyRequests with exponential backoff and jitter
            if status == 429 or code == "toomanyrequests" or "too many" in msg:
                if attempt >= max_retries:
                    raise
                retry_after = None
                try:
                    hdrs = getattr(e, "headers", None) or {}
                    retry_after = hdrs.get("retry-after") or hdrs.get("Retry-After")
                    if retry_after:
                        retry_after = float(retry_after)
                except Exception:
                    retry_after = None
                delay = retry_after or (base_delay * (2 ** attempt) + random.uniform(0, 0.5))
                time.sleep(delay)
                attempt += 1
                continue
            # Robust fallback matrix:
            # 1) forecast validation → align forecast at end
            # 2) final retry without forecast
            # Robust fallback matrix:
            # 1) If region complains about forecast fields (even when not sent), retry with explicit forecast window.
            # 2) If that still fails, retry without any forecast object.
            forecast_related = ("forecast" in msg) or ("timeforecastended" in msg) or ("timeforecaststarted" in msg)
            if e.status == 400 and forecast_related:
                # Try explicit forecast window
                try:
                    details_with_fc = oci.usage_api.models.RequestSummarizedUsagesDetails(
                        tenant_id=tenancy_ocid,
                        granularity=(q.granularity or "DAILY").upper(),
                        time_usage_started=ts_start,
                        time_usage_ended=ts_end,
                        query_type="COST",
                        group_by=group_by_param,
                        group_by_tag=group_by_tag_param,
                        filter=q.filter,
                        forecast=oci.usage_api.models.Forecast(
                            forecast_type="BASIC",
                            time_forecast_started=ts_end,
                            time_forecast_ended=ts_end
                        ),
                        compartment_depth=q.compartment_depth,
                        is_aggregate_by_time=True,
                    )
                    resp = clients.usage_api.request_summarized_usages(details_with_fc)
                    break
                except ServiceError:
                    # Final fallback: no forecast at all
                    details_no_fc = oci.usage_api.models.RequestSummarizedUsagesDetails(
                        tenant_id=tenancy_ocid,
                        granularity=(q.granularity or "DAILY").upper(),
                        time_usage_started=ts_start,
                        time_usage_ended=ts_end,
                        query_type="COST",
                        group_by=group_by_param,
                        group_by_tag=group_by_tag_param,
                        filter=q.filter,
                        forecast=None,
                        compartment_depth=q.compartment_depth,
                        is_aggregate_by_time=True,
                    )
                    resp = clients.usage_api.request_summarized_usages(details_no_fc)
                    break
            else:
            # 404 NotAuthorizedOrNotFound can also indicate a wrong tenantId was used.
            # Retry once with the config tenancy OCID to rule out a caller-provided mismatch.
                if e.status == 404:
                    try:
                        cfg_ten = clients.config.get('tenancy')
                        if cfg_ten and cfg_ten != tenancy_ocid:
                            details_retry = oci.usage_api.models.RequestSummarizedUsagesDetails(
                                tenant_id=cfg_ten,
                                granularity=(q.granularity or "DAILY").upper(),
                                time_usage_started=ts_start,
                                time_usage_ended=ts_end,
                                query_type="COST",
                                group_by=group_by_param,
                                group_by_tag=group_by_tag_param,
                                filter=q.filter,
                                forecast=forecast_obj,
                                compartment_depth=cd,
                                is_aggregate_by_time=True,
                            )
                            resp = clients.usage_api.request_summarized_usages(details_retry)
                            break
                        else:
                            raise
                    except ServiceError:
                        raise
                else:
                    raise

    # Convert response data to dict format
    if hasattr(resp.data, 'to_dict'):
        data = resp.data.to_dict()
    else:
        # Manually serialize the response data
        data = {
            'items': [
                {
                    'tenant_id': item.tenant_id if hasattr(item, 'tenant_id') else None,
                    'tenant_name': item.tenant_name if hasattr(item, 'tenant_name') else None,
                    'compartment_id': item.compartment_id if hasattr(item, 'compartment_id') else None,
                    'compartment_name': item.compartment_name if hasattr(item, 'compartment_name') else None,
                    'compartment_path': item.compartment_path if hasattr(item, 'compartment_path') else None,
                    'service': item.service if hasattr(item, 'service') else None,
                    'resource_name': item.resource_name if hasattr(item, 'resource_name') else None,
                    'resource_id': item.resource_id if hasattr(item, 'resource_id') else None,
                    'region': item.region if hasattr(item, 'region') else None,
                    'ad': item.ad if hasattr(item, 'ad') else None,
                    'product_sku': item.product_sku if hasattr(item, 'product_sku') else None,
                    'time_usage_started': str(item.time_usage_started) if hasattr(item, 'time_usage_started') else None,
                    'time_usage_ended': str(item.time_usage_ended) if hasattr(item, 'time_usage_ended') else None,
                    'computed_amount': float(getattr(item, 'computed_amount', 0) or 0.0),
                    'computed_quantity': float(getattr(item, 'computed_quantity', 0) or 0.0),
                    'unit_price': float(getattr(item, 'unit_price', 0) or 0.0),
                    'currency': item.currency if hasattr(item, 'currency') else 'USD',
                    'discount': float(getattr(item, 'discount', 0) or 0.0),
                    'overage': item.overage if hasattr(item, 'overage') else None,
                    'is_forecast': bool(item.is_forecast) if hasattr(item, 'is_forecast') else False,
                    'tags': item.tags if hasattr(item, 'tags') else None
                }
                for item in (resp.data.items if hasattr(resp.data, 'items') else [])
            ],
            # Preserve tenancy currency without forcing USD; caller may format or convert later
            'currency': getattr(resp.data, 'currency', None) if hasattr(resp.data, 'currency') else None,
            'group_by': getattr(resp.data, 'group_by', None) if hasattr(resp.data, 'group_by') else None
        }

        # Add forecast items if they exist
        if hasattr(resp.data, 'forecast_items') and resp.data.forecast_items:
            data['forecastItems'] = [
                {
                    'time_usage_started': str(item.time_usage_started) if hasattr(item, 'time_usage_started') else None,
                    'time_usage_ended': str(item.time_usage_ended) if hasattr(item, 'time_usage_ended') else None,
                    'computed_amount': float(getattr(item, 'computed_amount', 0) or 0.0),
                    'currency': item.currency if hasattr(item, 'currency') else 'USD'
                }
                for item in resp.data.forecast_items
            ]
    if _TTL > 0:
        _cache[key] = (now + _TTL, data)
    return data
