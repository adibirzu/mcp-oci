"""MCP Server: OCI SDK Introspection

Provides generic tools to introspect SDK methods for arbitrary clients, and
service-specific convenience tools following the pattern `oci:<service>:list-sdk-methods`.
"""

from typing import Any
from mcp_oci_common.name_registry import get_registry
import json

try:
    import oci  # type: ignore
except Exception:
    oci = None


SERVICE_CLIENTS: dict[str, list[str]] = {
    "identity": ["identity.IdentityClient"],
    "compute": ["core.ComputeClient"],
    "networking": ["core.VirtualNetworkClient"],
    "blockstorage": ["core.BlockstorageClient"],
    "objectstorage": ["object_storage.ObjectStorageClient"],
    "monitoring": ["monitoring.MonitoringClient", "monitoring.AlarmsClient", "monitoring.AlarmClient"],
    "loganalytics": ["log_analytics.LogAnalyticsClient"],
    "usageapi": ["usage_api.UsageapiClient"],
    "budgets": ["budget.BudgetClient"],
    "limits": ["limits.LimitsClient", "limits.QuotasClient"],
    "dns": ["dns.DnsClient"],
    "loadbalancer": ["load_balancer.LoadBalancerClient"],
    "filestorage": ["file_storage.FileStorageClient"],
    "apigateway": ["apigateway.GatewayClient"],
    "database": ["database.DatabaseClient"],
    "oke": ["container_engine.ContainerEngineClient"],
    "functions": ["functions.FunctionsManagementClient"],
    "events": ["events.EventsClient"],
    "streaming": ["streaming.StreamAdminClient"],
    "ons": ["ons.NotificationControlPlaneClient"],
    "vault": ["secrets.SecretsClient"],
    "kms": ["key_management.KmsManagementClient"],
    "resourcemanager": ["resource_manager.ResourceManagerClient"],
    "osub": ["osub_subscription.SubscriptionClient"],
}


def _resolve_client_class(path: str) -> Any:
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    module_path, cls_name = path.rsplit(".", 1)
    mod = oci
    for part in module_path.split("."):
        mod = getattr(mod, part)
    return getattr(mod, cls_name)


def _list_methods_of(obj: Any) -> list[str]:
    names: list[str] = []
    for name in dir(obj):
        if name.startswith("_"):
            continue
        ref = getattr(obj, name)
        if callable(ref):
            names.append(name)
    return sorted(names)


def register_tools() -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = [
        {
            "name": "oci_sdk_list_methods",
            "description": "List SDK methods for a given client class (e.g., usage_api.UsageapiClient).",
            "parameters": {
                "type": "object",
                "properties": {
                    "client_path": {"type": "string", "description": "Module.Class under oci, e.g., monitoring.MonitoringClient"},
                },
                "required": ["client_path"],
            },
            "handler": sdk_list_methods,
        },
        {
            "name": "mcp_registry_dump",
            "description": "Dump in-process name→OCID registry (counts and sample entries).",
            "parameters": {"type": "object", "properties": {}},
            "handler": registry_dump,
        },
        {
            "name": "mcp_registry_resolve",
            "description": "Resolve a resource name to OCID using the registry (no API calls).",
            "parameters": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["compartment","vcn","subnet","nsg","instance","user","cluster","application","stream"]},
                    "name": {"type": "string"},
                    "compartment_id": {"type": "string", "description": "Required for vcn/subnet/nsg/instance/application/stream lookups"}
                },
                "required": ["kind", "name"],
            },
            "handler": registry_resolve,
        },
        {
            "name": "mcp_registry_report",
            "description": "Summarize registry coverage and suggest warm-up actions.",
            "parameters": {"type": "object", "properties": {}},
            "handler": registry_report,
        },
        {
            "name": "mcp_warm_services",
            "description": "Warm the registry/cache by listing common resources (compartments, VCNs, subnets, instances, users, OKE clusters, Functions apps, streams, buckets).",
            "parameters": {
                "type": "object",
                "properties": {
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                    "compartment_id": {"type": "string"},
                    "limit": {"type": "integer", "default": 10}
                }
            },
            "handler": warm_services,
        },
        {
            "name": "mcp_warm_compartment",
            "description": "Warm a specific compartment deeply (VCNs, subnets, instances, LBs, functions, streams).",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                    "limit": {"type": "integer", "default": 20}
                },
                "required": ["compartment_id"],
            },
            "handler": warm_compartment,
        },
    ]
    # Add service-prefixed tools
    for service, candidates in SERVICE_CLIENTS.items():
        def _make_handler(paths: list[str]):
            def _handler() -> dict[str, Any]:
                out: dict[str, list[str]] = {}
                for p in paths:
                    try:
                        cls = _resolve_client_class(p)
                        out[p] = _list_methods_of(cls)
                    except Exception:
                        continue
                return {"clients": out}
            return _handler

        tools.append(
            {
                "name": f"oci_{service}_list_sdk_methods",
                "description": f"List SDK methods for common {service} clients (class-level introspection).",
                "parameters": {"type": "object", "properties": {}},
                "handler": _make_handler(candidates),
            }
        )
    return tools


def sdk_list_methods(client_path: str) -> dict[str, Any]:
    cls = _resolve_client_class(client_path)
    return {"methods": _list_methods_of(cls)}


def registry_dump() -> dict[str, Any]:
    reg = get_registry()
    # Show counts and up to 5 sample keys per mapping to keep output small
    def sample(d):
        keys = list(d.keys())
        return {"count": len(d), "sample_keys": keys[:5]}
    return {
        "compartments_by_name": sample(reg.compartments_by_name),
        "vcns_by_name": sample(reg.vcns_by_name),
        "subnets_by_name": sample(reg.subnets_by_name),
        "nsgs_by_name": sample(reg.nsgs_by_name),
        "instances_by_name": sample(reg.instances_by_name),
        "users_by_name": sample(reg.users_by_name),
        "clusters_by_name": sample(reg.clusters_by_name),
        "applications_by_name": sample(reg.applications_by_name),
        "streams_by_name": sample(reg.streams_by_name),
    }


def registry_resolve(kind: str, name: str, compartment_id: str | None = None) -> dict[str, Any]:
    reg = get_registry()
    ocid = None
    if kind == "compartment":
        ocid = reg.resolve_compartment(name)
    elif kind == "user":
        ocid = reg.resolve_user(name)
    elif kind == "vcn":
        if not compartment_id:
            return {"error": "compartment_id required for vcn lookup"}
        ocid = reg.resolve_vcn(compartment_id, name)
    elif kind == "subnet":
        if not compartment_id:
            return {"error": "compartment_id required for subnet lookup"}
        ocid = reg.resolve_subnet(compartment_id, name)
    elif kind == "nsg":
        if not compartment_id:
            return {"error": "compartment_id required for nsg lookup"}
        ocid = reg.resolve_nsg(compartment_id, name)
    elif kind == "instance":
        if not compartment_id:
            return {"error": "compartment_id required for instance lookup"}
        ids = reg.resolve_instance(compartment_id, name)
        return {"ocids": ids}
    elif kind == "cluster":
        if not compartment_id:
            return {"error": "compartment_id required for cluster lookup"}
        ocid = reg.resolve_cluster(compartment_id, name)
    elif kind == "application":
        if not compartment_id:
            return {"error": "compartment_id required for application lookup"}
        ocid = reg.resolve_application(compartment_id, name)
    elif kind == "stream":
        if not compartment_id:
            return {"error": "compartment_id required for stream lookup"}
        ocid = reg.resolve_stream(compartment_id, name)
    return {"ocid": ocid}


def registry_report() -> dict[str, Any]:
    reg = get_registry()
    def count(d):
        return len(d) if hasattr(d, '__len__') else 0
    report = {
        "compartments_by_name": count(reg.compartments_by_name),
        "vcns_by_name": count(reg.vcns_by_name),
        "subnets_by_name": count(reg.subnets_by_name),
        "nsgs_by_name": count(reg.nsgs_by_name),
        "instances_by_name": count(reg.instances_by_name),
        "users_by_name": count(reg.users_by_name),
        "clusters_by_name": count(reg.clusters_by_name),
        "applications_by_name": count(reg.applications_by_name),
        "streams_by_name": count(reg.streams_by_name),
    }
    suggestions: list[str] = []
    if report["compartments_by_name"] == 0:
        suggestions.append("Run mcp_warm_services to index compartment names")
    if report["vcns_by_name"] == 0:
        suggestions.append("Run mcp_warm_services for key compartments to index VCN names")
    if report["subnets_by_name"] == 0:
        suggestions.append("Run mcp_warm_compartment for specific compartments to index subnet names")
    if report["instances_by_name"] == 0:
        suggestions.append("Run mcp_warm_services with small limit to index instance names")
    if report["users_by_name"] == 0:
        suggestions.append("Run mcp_warm_services to index IAM users")
    if report["clusters_by_name"] == 0:
        suggestions.append("Run mcp_warm_services to index OKE clusters")
    if report["applications_by_name"] == 0:
        suggestions.append("Run mcp_warm_services to index Fn applications")
    if report["streams_by_name"] == 0:
        suggestions.append("Run mcp_warm_services to index streams")
    return {"counts": report, "suggestions": suggestions}


def warm_services(profile: str | None = None, region: str | None = None, compartment_id: str | None = None, limit: int = 10) -> dict[str, Any]:
    """Warm registry and caches by calling common list operations.

    Handles modules that return JSON strings (with_meta) and those that return dicts.
    """
    from mcp_oci_common.config import get_oci_config

    # Resolve tenancy if compartment_id not provided
    cfg = get_oci_config(profile_name=profile)
    if region:
        cfg["region"] = region
    tenancy = compartment_id or cfg.get("tenancy")

    results: dict[str, int] = {}

    def _load(x):
        try:
            return json.loads(x) if isinstance(x, str) else x
        except Exception:
            return x

    # IAM compartments (basis for name mapping)
    try:
        from mcp_oci_iam.server import list_compartments as _lc
        out = _load(_lc(compartment_id=tenancy, include_subtree=True, profile=profile, region=region))
        results["compartments"] = len((out or {}).get("items", []))
    except Exception:
        results["compartments"] = -1

    # Networking: VCNs + Subnets
    try:
        from mcp_oci_networking.server import list_vcns as _lv, list_subnets as _ls
        out = _load(_lv(compartment_id=tenancy, limit=limit, profile=profile, region=region))
        results["vcns"] = len((out or {}).get("items", []))
        out = _load(_ls(compartment_id=tenancy, limit=limit, profile=profile, region=region))
        results["subnets"] = len((out or {}).get("items", []))
    except Exception:
        results["vcns"] = results.get("vcns", -1)
        results["subnets"] = results.get("subnets", -1)

    # Compute instances (small cap)
    try:
        from mcp_oci_compute.server import list_instances as _li
        out = _li(compartment_id=tenancy, include_subtree=False, max_items=limit, profile=profile, region=region)
        results["instances"] = len((out or {}).get("items", []))
    except Exception:
        results["instances"] = -1

    # IAM users
    try:
        from mcp_oci_iam.server import list_users as _lu
        out = _load(_lu(compartment_id=tenancy, limit=limit, profile=profile, region=region))
        results["users"] = len((out or {}).get("items", []))
    except Exception:
        results["users"] = -1

    # OKE clusters
    try:
        from mcp_oci_oke.server import list_clusters as _lcl
        out = _load(_lcl(compartment_id=tenancy, limit=limit, profile=profile, region=region))
        results["clusters"] = len((out or {}).get("items", []))
    except Exception:
        results["clusters"] = -1

    # Functions applications
    try:
        from mcp_oci_functions.server import list_applications as _lapp
        out = _load(_lapp(compartment_id=tenancy, limit=limit, profile=profile, region=region))
        results["applications"] = len((out or {}).get("items", []))
    except Exception:
        results["applications"] = -1

    # Streams
    try:
        from mcp_oci_streaming.server import list_streams as _lst
        out = _load(_lst(compartment_id=tenancy, limit=limit, profile=profile, region=region))
        results["streams"] = len((out or {}).get("items", []))
    except Exception:
        results["streams"] = -1

    # Object Storage buckets
    try:
        from mcp_oci_objectstorage.server import get_namespace as _gn, list_buckets as _lb
        ns = (_load(_gn(profile=profile, region=region)) or {}).get("namespace")
        out = _load(_lb(namespace_name=ns, compartment_id=tenancy, limit=limit, profile=profile, region=region))
        results["buckets"] = len((out or {}).get("items", []))
    except Exception:
        results["buckets"] = -1

    # Load Balancers
    try:
        from mcp_oci_loadbalancer.server import list_load_balancers as _llb
        out = _load(_llb(compartment_id=tenancy, limit=limit, profile=profile, region=region))
        results["load_balancers"] = len((out or {}).get("items", []))
    except Exception:
        results["load_balancers"] = -1

    # Return summary
    return {"warmed": results}


def warm_compartment(compartment_id: str, profile: str | None = None, region: str | None = None, limit: int = 20) -> dict[str, Any]:
    """Warm a specific compartment: VCNs -> subnets, instances, load balancers, functions, streams.
    Returns counts warmed per resource type.
    """

    def _load(x):
        try:
            return json.loads(x) if isinstance(x, str) else x
        except Exception:
            return x

    sums: dict[str, int] = {}

    # VCNs and subnets
    try:
        from mcp_oci_networking.server import list_vcns as _lv, list_subnets as _ls
        vcns = (_load(_lv(compartment_id=compartment_id, limit=limit, profile=profile, region=region)) or {}).get("items", [])
        sums["vcns"] = len(vcns)
        sub_count = 0
        for v in vcns:
            vid = v.get("id") or v.get("_id")
            out = _load(_ls(compartment_id=compartment_id, vcn_id=vid, limit=limit, profile=profile, region=region))
            sub_count += len((out or {}).get("items", []))
        sums["subnets"] = sub_count
    except Exception:
        sums.setdefault("vcns", -1)
        sums.setdefault("subnets", -1)

    # Instances
    try:
        from mcp_oci_compute.server import list_instances as _li
        out = _li(compartment_id=compartment_id, include_subtree=False, max_items=limit, profile=profile, region=region)
        sums["instances"] = len((out or {}).get("items", []))
    except Exception:
        sums["instances"] = -1

    # Load balancers
    try:
        from mcp_oci_loadbalancer.server import list_load_balancers as _llb
        out = _load(_llb(compartment_id=compartment_id, limit=limit, profile=profile, region=region))
        sums["load_balancers"] = len((out or {}).get("items", []))
    except Exception:
        sums["load_balancers"] = -1

    # Functions applications
    try:
        from mcp_oci_functions.server import list_applications as _lapp
        out = _load(_lapp(compartment_id=compartment_id, limit=limit, profile=profile, region=region))
        sums["applications"] = len((out or {}).get("items", []))
    except Exception:
        sums["applications"] = -1

    # Streams
    try:
        from mcp_oci_streaming.server import list_streams as _lst
        out = _load(_lst(compartment_id=compartment_id, limit=limit, profile=profile, region=region))
        sums["streams"] = len((out or {}).get("items", []))
    except Exception:
        sums["streams"] = -1

    return {"warmed": sums}
