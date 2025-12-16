"""
OCI Object Storage MCP Server

Provides tools for:
- Listing and querying buckets
- Getting object sizes and counts
- Generating storage usage reports
- Discovering database backups stored in Object Storage

Environment Variables:
    OCI_PROFILE          - OCI config profile (default: DEFAULT)
    COMPARTMENT_OCID     - Default compartment OCID
    DEBUG                - Enable debug logging
    ALLOW_MUTATIONS      - Enable write operations
    OTEL_SERVICE_NAME    - Service name for tracing
    METRICS_PORT         - Prometheus metrics port (default: 8012)
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

# FastMCP framework
from fastmcp import FastMCP
from fastmcp.tools import Tool

# OCI SDK
import oci
from oci.pagination import list_call_get_all_results

# OpenTelemetry
from opentelemetry import trace

# Common utilities from mcp_oci_common
from mcp_oci_common import (
    get_oci_config,
    get_compartment_id,
    allow_mutations,
    validate_and_log_tools
)
from mcp_oci_common.session import get_client
from mcp_oci_common.observability import (
    init_tracing,
    init_metrics,
    tool_span,
    add_oci_call_attributes
)

# Set up tracing
os.environ.setdefault("OTEL_SERVICE_NAME", "oci-mcp-objectstorage")
init_tracing(service_name="oci-mcp-objectstorage")
init_metrics()
tracer = trace.get_tracer("oci-mcp-objectstorage")

# Logging setup
logging.basicConfig(level=logging.INFO if os.getenv('DEBUG') else logging.WARNING)
logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions
# =============================================================================

def _safe_serialize(obj):
    """Safely serialize OCI SDK objects and other complex types"""
    if obj is None:
        return None

    # Handle datetime objects
    if isinstance(obj, datetime):
        return obj.isoformat()

    # Handle OCI SDK objects
    if hasattr(obj, '__dict__'):
        try:
            if hasattr(obj, 'to_dict'):
                return obj.to_dict()
            elif hasattr(obj, '_data') and hasattr(obj._data, '__dict__'):
                return obj._data.__dict__
            else:
                result = {}
                for key, value in obj.__dict__.items():
                    if not key.startswith('_'):
                        result[key] = _safe_serialize(value)
                return result
        except Exception as e:
            return {"serialization_error": str(e), "original_type": str(type(obj))}

    # Handle lists, dicts, primitives recursively
    elif isinstance(obj, (list, tuple)):
        return [_safe_serialize(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: _safe_serialize(value) for key, value in obj.items()}
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    else:
        try:
            return str(obj)
        except Exception:
            return {"unknown_type": str(type(obj))}


def _get_namespace() -> str:
    """Get the Object Storage namespace for the tenancy"""
    config = get_oci_config()
    object_storage_client = get_client(oci.object_storage.ObjectStorageClient, region=config.get("region"))
    return object_storage_client.get_namespace().data


def _format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} EB"


# =============================================================================
# Tool Functions
# =============================================================================

def list_buckets(
    compartment_id: Optional[str] = None,
    region: Optional[str] = None,
    limit: int = 100
) -> List[Dict]:
    """
    List all Object Storage buckets in a compartment.

    Args:
        compartment_id: Compartment OCID (defaults to COMPARTMENT_OCID env var)
        region: OCI region (defaults to config region)
        limit: Maximum number of buckets to return

    Returns:
        List of bucket summaries with name, namespace, compartment, and time_created
    """
    with tool_span(tracer, "list_buckets", mcp_server="oci-mcp-objectstorage") as span:
        compartment = compartment_id or get_compartment_id()
        config = get_oci_config()
        object_storage_client = get_client(
            oci.object_storage.ObjectStorageClient,
            region=region or config.get("region")
        )

        try:
            namespace = _get_namespace()
            span.set_attribute("oci.namespace", namespace)

            add_oci_call_attributes(
                span,
                oci_service="ObjectStorage",
                oci_operation="ListBuckets",
                region=region or config.get("region"),
                endpoint=getattr(object_storage_client.base_client, "endpoint", ""),
            )

            response = list_call_get_all_results(
                object_storage_client.list_buckets,
                namespace_name=namespace,
                compartment_id=compartment,
                limit=limit
            )

            buckets = []
            for bucket in response.data:
                buckets.append({
                    "name": bucket.name,
                    "namespace": bucket.namespace,
                    "compartment_id": bucket.compartment_id,
                    "time_created": _safe_serialize(bucket.time_created),
                    "etag": bucket.etag,
                })

            span.set_attribute("buckets.count", len(buckets))
            return buckets

        except oci.exceptions.ServiceError as e:
            logger.error(f"Error listing buckets: {e}")
            span.record_exception(e)
            return [{"error": str(e)}]


def get_bucket(
    bucket_name: str,
    region: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get detailed information about a specific bucket.

    Args:
        bucket_name: Name of the bucket
        region: OCI region (defaults to config region)

    Returns:
        Bucket details including storage tier, versioning, encryption, etc.
    """
    with tool_span(tracer, "get_bucket", mcp_server="oci-mcp-objectstorage") as span:
        config = get_oci_config()
        object_storage_client = get_client(
            oci.object_storage.ObjectStorageClient,
            region=region or config.get("region")
        )

        try:
            namespace = _get_namespace()
            span.set_attribute("oci.namespace", namespace)
            span.set_attribute("bucket.name", bucket_name)

            add_oci_call_attributes(
                span,
                oci_service="ObjectStorage",
                oci_operation="GetBucket",
                region=region or config.get("region"),
                endpoint=getattr(object_storage_client.base_client, "endpoint", ""),
            )

            response = object_storage_client.get_bucket(
                namespace_name=namespace,
                bucket_name=bucket_name,
                fields=["approximateSize", "approximateCount", "autoTiering"]
            )

            bucket = response.data
            return {
                "name": bucket.name,
                "namespace": bucket.namespace,
                "compartment_id": bucket.compartment_id,
                "created_by": bucket.created_by,
                "time_created": _safe_serialize(bucket.time_created),
                "etag": bucket.etag,
                "public_access_type": bucket.public_access_type,
                "storage_tier": bucket.storage_tier,
                "object_events_enabled": bucket.object_events_enabled,
                "versioning": bucket.versioning,
                "is_read_only": bucket.is_read_only,
                "replication_enabled": bucket.replication_enabled,
                "approximate_count": bucket.approximate_count,
                "approximate_size": bucket.approximate_size,
                "approximate_size_human": _format_size(bucket.approximate_size) if bucket.approximate_size else "0 B",
                "auto_tiering": bucket.auto_tiering,
                "kms_key_id": bucket.kms_key_id,
                "freeform_tags": bucket.freeform_tags,
                "defined_tags": bucket.defined_tags,
            }

        except oci.exceptions.ServiceError as e:
            logger.error(f"Error getting bucket {bucket_name}: {e}")
            span.record_exception(e)
            return {"error": str(e)}


def list_objects(
    bucket_name: str,
    prefix: Optional[str] = None,
    delimiter: Optional[str] = None,
    limit: int = 1000,
    region: Optional[str] = None,
    include_size: bool = True
) -> Dict[str, Any]:
    """
    List objects in a bucket with optional filtering.

    Args:
        bucket_name: Name of the bucket
        prefix: Filter objects by prefix (e.g., "backups/", "db-backups/")
        delimiter: Delimiter for pseudo-directory listing (e.g., "/")
        limit: Maximum number of objects to return
        region: OCI region
        include_size: Include size information for each object

    Returns:
        Dictionary with objects list, prefixes (if delimiter used), and summary
    """
    with tool_span(tracer, "list_objects", mcp_server="oci-mcp-objectstorage") as span:
        config = get_oci_config()
        object_storage_client = get_client(
            oci.object_storage.ObjectStorageClient,
            region=region or config.get("region")
        )

        try:
            namespace = _get_namespace()
            span.set_attribute("oci.namespace", namespace)
            span.set_attribute("bucket.name", bucket_name)
            if prefix:
                span.set_attribute("filter.prefix", prefix)

            add_oci_call_attributes(
                span,
                oci_service="ObjectStorage",
                oci_operation="ListObjects",
                region=region or config.get("region"),
                endpoint=getattr(object_storage_client.base_client, "endpoint", ""),
            )

            kwargs = {
                "namespace_name": namespace,
                "bucket_name": bucket_name,
                "limit": limit,
            }
            if prefix:
                kwargs["prefix"] = prefix
            if delimiter:
                kwargs["delimiter"] = delimiter

            # For large buckets, use pagination
            all_objects = []
            prefixes = []
            next_start = None
            total_size = 0

            while True:
                if next_start:
                    kwargs["start"] = next_start

                response = object_storage_client.list_objects(**kwargs)
                data = response.data

                for obj in data.objects:
                    obj_info = {
                        "name": obj.name,
                        "time_created": _safe_serialize(obj.time_created),
                        "time_modified": _safe_serialize(obj.time_modified),
                        "etag": obj.etag,
                        "md5": obj.md5,
                        "storage_tier": obj.storage_tier,
                        "archival_state": obj.archival_state,
                    }
                    if include_size and obj.size is not None:
                        obj_info["size"] = obj.size
                        obj_info["size_human"] = _format_size(obj.size)
                        total_size += obj.size

                    all_objects.append(obj_info)

                if data.prefixes:
                    prefixes.extend(data.prefixes)

                if len(all_objects) >= limit:
                    break

                next_start = data.next_start_with
                if not next_start:
                    break

            result = {
                "bucket_name": bucket_name,
                "namespace": namespace,
                "object_count": len(all_objects),
                "total_size": total_size,
                "total_size_human": _format_size(total_size),
                "objects": all_objects[:limit],
            }

            if prefixes:
                result["prefixes"] = prefixes

            if prefix:
                result["filter_prefix"] = prefix

            span.set_attribute("objects.count", len(all_objects))
            span.set_attribute("objects.total_size", total_size)

            return result

        except oci.exceptions.ServiceError as e:
            logger.error(f"Error listing objects in {bucket_name}: {e}")
            span.record_exception(e)
            return {"error": str(e)}


def get_bucket_usage(
    bucket_name: str,
    region: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get usage statistics for a bucket including size, object count, and storage breakdown.

    Args:
        bucket_name: Name of the bucket
        region: OCI region

    Returns:
        Usage statistics including size, count, and storage tier breakdown
    """
    with tool_span(tracer, "get_bucket_usage", mcp_server="oci-mcp-objectstorage") as span:
        config = get_oci_config()
        object_storage_client = get_client(
            oci.object_storage.ObjectStorageClient,
            region=region or config.get("region")
        )

        try:
            namespace = _get_namespace()
            span.set_attribute("oci.namespace", namespace)
            span.set_attribute("bucket.name", bucket_name)

            # Get bucket with size info
            bucket_response = object_storage_client.get_bucket(
                namespace_name=namespace,
                bucket_name=bucket_name,
                fields=["approximateSize", "approximateCount"]
            )
            bucket = bucket_response.data

            # List objects to get detailed breakdown
            objects_response = object_storage_client.list_objects(
                namespace_name=namespace,
                bucket_name=bucket_name,
                limit=1000
            )

            # Calculate storage tier breakdown
            tier_stats = {}
            total_size = 0
            object_count = 0

            all_objects = objects_response.data.objects
            next_start = objects_response.data.next_start_with

            # Paginate through all objects for accurate stats
            while True:
                for obj in all_objects:
                    tier = obj.storage_tier or "Standard"
                    if tier not in tier_stats:
                        tier_stats[tier] = {"count": 0, "size": 0}
                    tier_stats[tier]["count"] += 1
                    tier_stats[tier]["size"] += obj.size or 0
                    total_size += obj.size or 0
                    object_count += 1

                if not next_start:
                    break

                objects_response = object_storage_client.list_objects(
                    namespace_name=namespace,
                    bucket_name=bucket_name,
                    start=next_start,
                    limit=1000
                )
                all_objects = objects_response.data.objects
                next_start = objects_response.data.next_start_with

            # Format tier stats
            for tier in tier_stats:
                tier_stats[tier]["size_human"] = _format_size(tier_stats[tier]["size"])

            return {
                "bucket_name": bucket_name,
                "namespace": namespace,
                "compartment_id": bucket.compartment_id,
                "storage_tier": bucket.storage_tier,
                "object_count": object_count,
                "approximate_count": bucket.approximate_count,
                "total_size": total_size,
                "total_size_human": _format_size(total_size),
                "approximate_size": bucket.approximate_size,
                "approximate_size_human": _format_size(bucket.approximate_size) if bucket.approximate_size else "0 B",
                "tier_breakdown": tier_stats,
                "versioning": bucket.versioning,
                "auto_tiering": bucket.auto_tiering,
            }

        except oci.exceptions.ServiceError as e:
            logger.error(f"Error getting usage for bucket {bucket_name}: {e}")
            span.record_exception(e)
            return {"error": str(e)}


def get_storage_report(
    compartment_id: Optional[str] = None,
    region: Optional[str] = None,
    include_object_details: bool = False
) -> Dict[str, Any]:
    """
    Generate a comprehensive storage report for all buckets in a compartment.

    Args:
        compartment_id: Compartment OCID (defaults to COMPARTMENT_OCID env var)
        region: OCI region
        include_object_details: Include detailed object list per bucket (slower)

    Returns:
        Comprehensive report with all buckets, sizes, and usage statistics
    """
    with tool_span(tracer, "get_storage_report", mcp_server="oci-mcp-objectstorage") as span:
        compartment = compartment_id or get_compartment_id()
        config = get_oci_config()
        object_storage_client = get_client(
            oci.object_storage.ObjectStorageClient,
            region=region or config.get("region")
        )

        try:
            namespace = _get_namespace()
            span.set_attribute("oci.namespace", namespace)

            # List all buckets
            buckets_response = list_call_get_all_results(
                object_storage_client.list_buckets,
                namespace_name=namespace,
                compartment_id=compartment
            )

            report = {
                "namespace": namespace,
                "compartment_id": compartment,
                "region": region or config.get("region"),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_buckets": len(buckets_response.data),
                "total_size": 0,
                "total_objects": 0,
                "buckets": [],
            }

            tier_totals = {}

            for bucket_summary in buckets_response.data:
                # Get detailed bucket info
                bucket_response = object_storage_client.get_bucket(
                    namespace_name=namespace,
                    bucket_name=bucket_summary.name,
                    fields=["approximateSize", "approximateCount"]
                )
                bucket = bucket_response.data

                bucket_info = {
                    "name": bucket.name,
                    "storage_tier": bucket.storage_tier,
                    "time_created": _safe_serialize(bucket.time_created),
                    "approximate_count": bucket.approximate_count,
                    "approximate_size": bucket.approximate_size,
                    "approximate_size_human": _format_size(bucket.approximate_size) if bucket.approximate_size else "0 B",
                    "versioning": bucket.versioning,
                    "public_access_type": bucket.public_access_type,
                    "auto_tiering": bucket.auto_tiering,
                }

                if bucket.approximate_size:
                    report["total_size"] += bucket.approximate_size
                if bucket.approximate_count:
                    report["total_objects"] += bucket.approximate_count

                # Track tier totals
                tier = bucket.storage_tier or "Standard"
                if tier not in tier_totals:
                    tier_totals[tier] = {"count": 0, "size": 0, "buckets": 0}
                tier_totals[tier]["buckets"] += 1
                tier_totals[tier]["count"] += bucket.approximate_count or 0
                tier_totals[tier]["size"] += bucket.approximate_size or 0

                if include_object_details:
                    # Get top-level prefixes for directory structure
                    objects_response = object_storage_client.list_objects(
                        namespace_name=namespace,
                        bucket_name=bucket_summary.name,
                        delimiter="/",
                        limit=100
                    )
                    bucket_info["top_level_prefixes"] = objects_response.data.prefixes or []
                    bucket_info["root_objects_count"] = len(objects_response.data.objects)

                report["buckets"].append(bucket_info)

            # Format tier totals
            for tier in tier_totals:
                tier_totals[tier]["size_human"] = _format_size(tier_totals[tier]["size"])

            report["total_size_human"] = _format_size(report["total_size"])
            report["tier_breakdown"] = tier_totals

            # Sort buckets by size (largest first)
            report["buckets"].sort(
                key=lambda x: x.get("approximate_size") or 0,
                reverse=True
            )

            span.set_attribute("report.buckets", report["total_buckets"])
            span.set_attribute("report.total_size", report["total_size"])

            return report

        except oci.exceptions.ServiceError as e:
            logger.error(f"Error generating storage report: {e}")
            span.record_exception(e)
            return {"error": str(e)}


def list_db_backups(
    compartment_id: Optional[str] = None,
    region: Optional[str] = None,
    bucket_prefix: Optional[str] = None
) -> Dict[str, Any]:
    """
    List database backups stored in Object Storage.

    Searches for backups in buckets with common naming patterns:
    - Buckets containing "backup", "dbbackup", "db-backup"
    - Objects with .bak, .dmp, .exp, .rman extensions
    - Autonomous Database backups in standard OCI backup buckets

    Args:
        compartment_id: Compartment OCID
        region: OCI region
        bucket_prefix: Filter buckets by prefix (e.g., "backup-", "db-")

    Returns:
        List of discovered database backups with metadata
    """
    with tool_span(tracer, "list_db_backups", mcp_server="oci-mcp-objectstorage") as span:
        compartment = compartment_id or get_compartment_id()
        config = get_oci_config()
        object_storage_client = get_client(
            oci.object_storage.ObjectStorageClient,
            region=region or config.get("region")
        )

        try:
            namespace = _get_namespace()
            span.set_attribute("oci.namespace", namespace)

            # List all buckets
            buckets_response = list_call_get_all_results(
                object_storage_client.list_buckets,
                namespace_name=namespace,
                compartment_id=compartment
            )

            # Backup-related keywords and extensions
            backup_keywords = ["backup", "db", "database", "rman", "export", "dump", "adb"]
            backup_extensions = [".bak", ".dmp", ".exp", ".rman", ".dbf", ".arc", ".ctl", ".log"]

            discovered_backups = []
            backup_buckets = []

            for bucket_summary in buckets_response.data:
                bucket_name = bucket_summary.name.lower()

                # Check if bucket matches prefix filter
                if bucket_prefix and not bucket_summary.name.lower().startswith(bucket_prefix.lower()):
                    continue

                # Check if bucket name suggests backup content
                is_backup_bucket = any(kw in bucket_name for kw in backup_keywords)

                if is_backup_bucket:
                    backup_buckets.append(bucket_summary.name)

                    # List objects in backup bucket
                    try:
                        objects_response = object_storage_client.list_objects(
                            namespace_name=namespace,
                            bucket_name=bucket_summary.name,
                            limit=500
                        )

                        for obj in objects_response.data.objects:
                            obj_name_lower = obj.name.lower()

                            # Check if object looks like a backup
                            is_backup_file = (
                                any(ext in obj_name_lower for ext in backup_extensions) or
                                any(kw in obj_name_lower for kw in backup_keywords)
                            )

                            if is_backup_file:
                                backup_type = "unknown"
                                if ".dmp" in obj_name_lower or "datapump" in obj_name_lower:
                                    backup_type = "Data Pump Export"
                                elif ".rman" in obj_name_lower or "rman" in obj_name_lower:
                                    backup_type = "RMAN Backup"
                                elif ".bak" in obj_name_lower:
                                    backup_type = "Database Backup"
                                elif "adb" in obj_name_lower or "autonomous" in bucket_name:
                                    backup_type = "Autonomous Database Backup"
                                elif ".arc" in obj_name_lower:
                                    backup_type = "Archive Log"
                                elif ".ctl" in obj_name_lower:
                                    backup_type = "Control File"

                                discovered_backups.append({
                                    "bucket_name": bucket_summary.name,
                                    "object_name": obj.name,
                                    "backup_type": backup_type,
                                    "size": obj.size,
                                    "size_human": _format_size(obj.size) if obj.size else "0 B",
                                    "time_created": _safe_serialize(obj.time_created),
                                    "time_modified": _safe_serialize(obj.time_modified),
                                    "storage_tier": obj.storage_tier,
                                    "archival_state": obj.archival_state,
                                })

                    except oci.exceptions.ServiceError as e:
                        logger.warning(f"Error listing objects in {bucket_summary.name}: {e}")
                        continue

            # Calculate summary statistics
            total_size = sum(b.get("size", 0) or 0 for b in discovered_backups)
            backup_types = {}
            for backup in discovered_backups:
                bt = backup["backup_type"]
                if bt not in backup_types:
                    backup_types[bt] = {"count": 0, "size": 0}
                backup_types[bt]["count"] += 1
                backup_types[bt]["size"] += backup.get("size", 0) or 0

            for bt in backup_types:
                backup_types[bt]["size_human"] = _format_size(backup_types[bt]["size"])

            result = {
                "namespace": namespace,
                "compartment_id": compartment,
                "backup_buckets_found": len(backup_buckets),
                "backup_buckets": backup_buckets,
                "total_backups": len(discovered_backups),
                "total_size": total_size,
                "total_size_human": _format_size(total_size),
                "backup_types": backup_types,
                "backups": sorted(
                    discovered_backups,
                    key=lambda x: x.get("time_modified") or "",
                    reverse=True
                )[:100],  # Return latest 100 backups
            }

            span.set_attribute("backups.count", len(discovered_backups))
            span.set_attribute("backups.total_size", total_size)

            return result

        except oci.exceptions.ServiceError as e:
            logger.error(f"Error listing DB backups: {e}")
            span.record_exception(e)
            return {"error": str(e)}


def get_backup_details(
    bucket_name: str,
    object_name: str,
    region: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get detailed information about a specific backup object.

    Args:
        bucket_name: Name of the bucket containing the backup
        object_name: Name of the backup object
        region: OCI region

    Returns:
        Detailed backup information including metadata, size, and download info
    """
    with tool_span(tracer, "get_backup_details", mcp_server="oci-mcp-objectstorage") as span:
        config = get_oci_config()
        object_storage_client = get_client(
            oci.object_storage.ObjectStorageClient,
            region=region or config.get("region")
        )

        try:
            namespace = _get_namespace()
            span.set_attribute("oci.namespace", namespace)
            span.set_attribute("bucket.name", bucket_name)
            span.set_attribute("object.name", object_name)

            add_oci_call_attributes(
                span,
                oci_service="ObjectStorage",
                oci_operation="HeadObject",
                region=region or config.get("region"),
                endpoint=getattr(object_storage_client.base_client, "endpoint", ""),
            )

            # Get object metadata (head request - doesn't download content)
            response = object_storage_client.head_object(
                namespace_name=namespace,
                bucket_name=bucket_name,
                object_name=object_name
            )

            headers = response.headers

            # Determine backup type from name
            obj_name_lower = object_name.lower()
            backup_type = "unknown"
            if ".dmp" in obj_name_lower:
                backup_type = "Data Pump Export"
            elif ".rman" in obj_name_lower or "rman" in obj_name_lower:
                backup_type = "RMAN Backup"
            elif ".bak" in obj_name_lower:
                backup_type = "Database Backup"
            elif "adb" in obj_name_lower:
                backup_type = "Autonomous Database Backup"
            elif ".arc" in obj_name_lower:
                backup_type = "Archive Log"
            elif ".ctl" in obj_name_lower:
                backup_type = "Control File"

            return {
                "bucket_name": bucket_name,
                "object_name": object_name,
                "namespace": namespace,
                "backup_type": backup_type,
                "content_length": int(headers.get("content-length", 0)),
                "size_human": _format_size(int(headers.get("content-length", 0))),
                "content_type": headers.get("content-type"),
                "content_md5": headers.get("content-md5"),
                "etag": headers.get("etag"),
                "storage_tier": headers.get("storage-tier"),
                "archival_state": headers.get("archival-state"),
                "time_created": headers.get("opc-meta-last-modified"),
                "last_modified": headers.get("last-modified"),
                "version_id": headers.get("version-id"),
                "opc_meta": {
                    k.replace("opc-meta-", ""): v
                    for k, v in headers.items()
                    if k.startswith("opc-meta-")
                },
            }

        except oci.exceptions.ServiceError as e:
            logger.error(f"Error getting backup details: {e}")
            span.record_exception(e)
            return {"error": str(e)}


def create_preauthenticated_request(
    bucket_name: str,
    object_name: str,
    access_type: str = "ObjectRead",
    expiration_hours: int = 24,
    region: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a Pre-Authenticated Request (PAR) for accessing a backup object.

    Args:
        bucket_name: Name of the bucket
        object_name: Name of the object
        access_type: Type of access - ObjectRead, ObjectWrite, ObjectReadWrite
        expiration_hours: Hours until the PAR expires (default: 24)
        region: OCI region

    Returns:
        PAR details including the access URI
    """
    with tool_span(tracer, "create_preauthenticated_request", mcp_server="oci-mcp-objectstorage") as span:
        if not allow_mutations():
            return {"error": "Mutations not allowed (set ALLOW_MUTATIONS=true)"}

        config = get_oci_config()
        object_storage_client = get_client(
            oci.object_storage.ObjectStorageClient,
            region=region or config.get("region")
        )

        try:
            namespace = _get_namespace()
            span.set_attribute("oci.namespace", namespace)
            span.set_attribute("bucket.name", bucket_name)
            span.set_attribute("object.name", object_name)

            add_oci_call_attributes(
                span,
                oci_service="ObjectStorage",
                oci_operation="CreatePreauthenticatedRequest",
                region=region or config.get("region"),
                endpoint=getattr(object_storage_client.base_client, "endpoint", ""),
            )

            # Calculate expiration
            from datetime import timedelta
            expiration = datetime.now(timezone.utc) + timedelta(hours=expiration_hours)

            par_details = oci.object_storage.models.CreatePreauthenticatedRequestDetails(
                name=f"par-{object_name}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                access_type=access_type,
                time_expires=expiration,
                object_name=object_name,
            )

            response = object_storage_client.create_preauthenticated_request(
                namespace_name=namespace,
                bucket_name=bucket_name,
                create_preauthenticated_request_details=par_details
            )

            par = response.data
            return {
                "id": par.id,
                "name": par.name,
                "access_type": par.access_type,
                "object_name": par.object_name,
                "bucket_name": bucket_name,
                "time_created": _safe_serialize(par.time_created),
                "time_expires": _safe_serialize(par.time_expires),
                "access_uri": par.access_uri,
                "full_path": par.full_path,
            }

        except oci.exceptions.ServiceError as e:
            logger.error(f"Error creating PAR: {e}")
            span.record_exception(e)
            return {"error": str(e)}


# =============================================================================
# Tool Registration
# =============================================================================

tools = [
    Tool.from_function(
        fn=lambda: {"status": "ok", "server": "oci-mcp-objectstorage", "pid": os.getpid()},
        name="healthcheck",
        description="Lightweight readiness/liveness check for the Object Storage server"
    ),
    Tool.from_function(
        fn=lambda: (lambda _cfg=get_oci_config(): {
            "server": "oci-mcp-objectstorage",
            "ok": True,
            "region": _cfg.get("region"),
            "profile": os.getenv("OCI_PROFILE") or "DEFAULT",
            "namespace": _get_namespace(),
            "tools": [t.name for t in tools]
        })(),
        name="doctor",
        description="Return server health, config summary, namespace, and available tools"
    ),
    Tool.from_function(
        fn=list_buckets,
        name="list_buckets",
        description="List all Object Storage buckets in a compartment"
    ),
    Tool.from_function(
        fn=get_bucket,
        name="get_bucket",
        description="Get detailed information about a specific bucket including size and object count"
    ),
    Tool.from_function(
        fn=list_objects,
        name="list_objects",
        description="List objects in a bucket with size information and optional filtering"
    ),
    Tool.from_function(
        fn=get_bucket_usage,
        name="get_bucket_usage",
        description="Get usage statistics for a bucket including size breakdown by storage tier"
    ),
    Tool.from_function(
        fn=get_storage_report,
        name="get_storage_report",
        description="Generate comprehensive storage report for all buckets in a compartment"
    ),
    Tool.from_function(
        fn=list_db_backups,
        name="list_db_backups",
        description="List database backups stored in Object Storage (searches backup-related buckets)"
    ),
    Tool.from_function(
        fn=get_backup_details,
        name="get_backup_details",
        description="Get detailed information about a specific backup object"
    ),
    Tool.from_function(
        fn=create_preauthenticated_request,
        name="create_preauthenticated_request",
        description="Create a Pre-Authenticated Request (PAR) for secure access to a backup object"
    ),
]


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    # Lazy imports for optional dependencies
    try:
        from prometheus_client import start_http_server as _start_http_server
    except Exception:
        _start_http_server = None
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor as _FastAPIInstrumentor
    except Exception:
        _FastAPIInstrumentor = None

    # Start Prometheus metrics server
    if _start_http_server:
        try:
            _start_http_server(int(os.getenv("METRICS_PORT", "8012")))
        except Exception:
            pass

    # Validate MCP tool names at startup
    if not validate_and_log_tools(tools, "oci-mcp-objectstorage"):
        logging.error("MCP tool validation failed. Server will not start.")
        exit(1)

    # Apply privacy masking to all tools
    try:
        from mcp_oci_common.privacy import privacy_enabled as _pe, redact_payload as _rp
        from fastmcp.tools import Tool as _Tool
        _wrapped = []
        for _t in tools:
            _f = getattr(_t, "func", None) or getattr(_t, "handler", None)
            if not _f:
                _wrapped.append(_t)
                continue

            def _mk(f):
                def _w(*a, **k):
                    out = f(*a, **k)
                    return _rp(out) if _pe() else out
                _w.__name__ = getattr(f, "__name__", "tool")
                _w.__doc__ = getattr(f, "__doc__", "")
                return _w
            _wrapped.append(_Tool.from_function(_mk(_f), name=_t.name, description=_t.description))
        tools = _wrapped
    except Exception:
        pass

    # Create and run FastMCP server
    mcp = FastMCP(tools=tools, name="oci-mcp-objectstorage")

    # Optional OpenTelemetry instrumentation
    if _FastAPIInstrumentor:
        try:
            if hasattr(mcp, "app"):
                _FastAPIInstrumentor.instrument_app(getattr(mcp, "app"))
            elif hasattr(mcp, "fastapi_app"):
                _FastAPIInstrumentor.instrument_app(getattr(mcp, "fastapi_app"))
            else:
                _FastAPIInstrumentor().instrument()
        except Exception:
            pass

    # Optional Pyroscope profiling
    try:
        ENABLE_PYROSCOPE = os.getenv("ENABLE_PYROSCOPE", "false").lower() in ("1", "true", "yes", "on")
        if ENABLE_PYROSCOPE:
            import pyroscope
            pyroscope.configure(
                application_name=os.getenv("PYROSCOPE_APP_NAME", "oci-mcp-objectstorage"),
                server_address=os.getenv("PYROSCOPE_SERVER_ADDRESS", "http://pyroscope:4040"),
                sample_rate=int(os.getenv("PYROSCOPE_SAMPLE_RATE", "100")),
                detect_subprocesses=True,
                enable_logging=True,
            )
    except Exception:
        pass

    mcp.run()
