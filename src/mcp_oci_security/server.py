"""MCP Server: OCI Security (Well-Architected Style)

Aggregates security posture information across Cloud Guard, Security Zones,
Vulnerability Scanning, KMS, and IAM to provide quick findings and summaries.
"""

from typing import Any, Dict, List, Optional
from mcp_oci_common import make_client
from mcp_oci_common.response import with_meta

try:
    import oci  # type: ignore
except Exception:
    oci = None


def _client_or_none(factory):
    try:
        return factory()
    except Exception:
        return None


def register_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "oci:security:list-cloud-guard-problems",
            "description": "List Cloud Guard problems in a compartment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "lifecycle_detail": {"type": "string"},
                    "risk_level": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": list_cloud_guard_problems,
        },
        {
            "name": "oci:security:list-security-zones",
            "description": "List Security Zones in a compartment (if supported).",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": list_security_zones,
        },
        {
            "name": "oci:security:list-host-scan-results",
            "description": "List Vulnerability Scanning host scan results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
            },
            "handler": list_host_scan_results,
        },
        {
            "name": "oci:security:list-container-scan-results",
            "description": "List Vulnerability Scanning container scan results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
            },
            "handler": list_container_scan_results,
        },
        {
            "name": "oci:security:list-kms-keys",
            "description": "List KMS keys in a vault.",
            "parameters": {
                "type": "object",
                "properties": {
                    "management_endpoint": {"type": "string", "description": "KMS management endpoint URL for the vault"},
                    "compartment_id": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["management_endpoint"],
            },
            "handler": list_kms_keys,
        },
        {
            "name": "oci:security:summary",
            "description": "High-level security summary across Cloud Guard, Security Zones, VSS, and KMS.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "management_endpoint": {"type": "string", "description": "Vault KMS management endpoint (optional)"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": summary,
        },
    ]


def _cg_client(profile: Optional[str], region: Optional[str]):
    if oci is None:
        return None
    return make_client(oci.cloud_guard.CloudGuardClient, profile=profile, region=region)


def _sz_client(profile: Optional[str], region: Optional[str]):
    if oci is None:
        return None
    # Security Zones client can be under security_zone module
    try:
        return make_client(oci.security_zone.SecurityZonesClient, profile=profile, region=region)
    except Exception:
        return None


def _vss_client(profile: Optional[str], region: Optional[str]):
    if oci is None:
        return None
    try:
        return make_client(oci.vulnerability_scanning.VulnerabilityScanningClient, profile=profile, region=region)
    except Exception:
        return None


def list_cloud_guard_problems(compartment_id: str, lifecycle_detail: Optional[str] = None,
                              risk_level: Optional[str] = None, limit: Optional[int] = None,
                              page: Optional[str] = None, profile: Optional[str] = None,
                              region: Optional[str] = None) -> Dict[str, Any]:
    client = _cg_client(profile, region)
    if client is None:
        raise RuntimeError("Cloud Guard client not available; ensure SDK supports cloud_guard")
    kwargs: Dict[str, Any] = {"compartment_id": compartment_id}
    if lifecycle_detail:
        kwargs["lifecycle_detail"] = lifecycle_detail
    if risk_level:
        kwargs["risk_level"] = risk_level
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_problems(**kwargs)
    items = [p.__dict__ for p in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def list_security_zones(compartment_id: str, limit: Optional[int] = None, page: Optional[str] = None,
                        profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    client = _sz_client(profile, region)
    if client is None:
        raise RuntimeError("Security Zones client not available; ensure SDK supports security_zone")
    kwargs: Dict[str, Any] = {"compartment_id": compartment_id}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    # Try possible method spellings
    for name in ("list_security_zones", "list_zones"):
        method = getattr(client, name, None)
        if method is None:
            continue
        resp = method(**kwargs)
        items = [z.__dict__ for z in getattr(resp, "data", [])]
        next_page = getattr(resp, "opc_next_page", None)
        return with_meta(resp, {"items": items}, next_page=next_page)
    raise RuntimeError("Security Zones list method not available in SDK")


def list_host_scan_results(compartment_id: Optional[str] = None, limit: Optional[int] = None,
                           page: Optional[str] = None, profile: Optional[str] = None,
                           region: Optional[str] = None) -> Dict[str, Any]:
    client = _vss_client(profile, region)
    if client is None:
        raise RuntimeError("Vulnerability Scanning client not available")
    kwargs: Dict[str, Any] = {}
    if compartment_id:
        kwargs["compartment_id"] = compartment_id
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    method = getattr(client, "list_host_scan_results", None)
    if method is None:
        raise RuntimeError("list_host_scan_results not available in SDK")
    resp = method(**kwargs)
    items = [r.__dict__ for r in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def list_container_scan_results(compartment_id: Optional[str] = None, limit: Optional[int] = None,
                                page: Optional[str] = None, profile: Optional[str] = None,
                                region: Optional[str] = None) -> Dict[str, Any]:
    client = _vss_client(profile, region)
    if client is None:
        raise RuntimeError("Vulnerability Scanning client not available")
    kwargs: Dict[str, Any] = {}
    if compartment_id:
        kwargs["compartment_id"] = compartment_id
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    method = getattr(client, "list_container_scan_results", None)
    if method is None:
        raise RuntimeError("list_container_scan_results not available in SDK")
    resp = method(**kwargs)
    items = [r.__dict__ for r in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def list_kms_keys(management_endpoint: str, compartment_id: Optional[str] = None, limit: Optional[int] = None,
                  page: Optional[str] = None, profile: Optional[str] = None,
                  region: Optional[str] = None) -> Dict[str, Any]:
    if oci is None:
        raise RuntimeError("OCI SDK not available")
    # KMS clients take kms_endpoint not region
    cfg = oci.config.from_file(profile_name=profile)
    if region:
        cfg["region"] = region
    kms = oci.key_management.KmsManagementClient(config=cfg, service_endpoint=management_endpoint)
    kwargs: Dict[str, Any] = {}
    if compartment_id:
        kwargs["compartment_id"] = compartment_id
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = kms.list_keys(**kwargs)
    items = [k.__dict__ for k in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def summary(compartment_id: str, management_endpoint: Optional[str] = None,
            profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    # Cloud Guard problems
    try:
        cg = list_cloud_guard_problems(compartment_id=compartment_id, profile=profile, region=region, limit=50)
        out["cloud_guard_problems_count"] = len(cg.get("items", []))
    except Exception as e:
        out["cloud_guard_problems_error"] = str(e)
    # Security Zones
    try:
        sz = list_security_zones(compartment_id=compartment_id, profile=profile, region=region, limit=50)
        out["security_zones_count"] = len(sz.get("items", []))
    except Exception as e:
        out["security_zones_error"] = str(e)
    # VSS Host scans
    try:
        vss = list_host_scan_results(compartment_id=compartment_id, profile=profile, region=region, limit=20)
        out["host_scan_results_count"] = len(vss.get("items", []))
    except Exception as e:
        out["host_scan_results_error"] = str(e)
    # KMS keys
    try:
        if management_endpoint:
            kms = list_kms_keys(management_endpoint=management_endpoint, profile=profile, region=region, limit=20)
            out["kms_keys_count"] = len(kms.get("items", []))
    except Exception as e:
        out["kms_keys_error"] = str(e)
    return out
