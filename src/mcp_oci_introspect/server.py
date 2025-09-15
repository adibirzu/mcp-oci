"""MCP Server: OCI SDK Introspection

Provides generic tools to introspect SDK methods for arbitrary clients, and
service-specific convenience tools following the pattern `oci:<service>:list-sdk-methods`.
"""

from typing import Any, Dict, List, Optional

try:
    import oci  # type: ignore
except Exception:
    oci = None


SERVICE_CLIENTS: Dict[str, List[str]] = {
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


def _list_methods_of(obj: Any) -> List[str]:
    names: List[str] = []
    for name in dir(obj):
        if name.startswith("_"):
            continue
        ref = getattr(obj, name)
        if callable(ref):
            names.append(name)
    return sorted(names)


def register_tools() -> List[Dict[str, Any]]:
    tools: List[Dict[str, Any]] = [
        {
            "name": "oci:sdk:list-methods",
            "description": "List SDK methods for a given client class (e.g., usage_api.UsageapiClient).",
            "parameters": {
                "type": "object",
                "properties": {
                    "client_path": {"type": "string", "description": "Module.Class under oci, e.g., monitoring.MonitoringClient"},
                },
                "required": ["client_path"],
            },
            "handler": sdk_list_methods,
        }
    ]
    # Add service-prefixed tools
    for service, candidates in SERVICE_CLIENTS.items():
        def _make_handler(paths: List[str]):
            def _handler() -> Dict[str, Any]:
                out: Dict[str, List[str]] = {}
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
                "name": f"oci:{service}:list-sdk-methods",
                "description": f"List SDK methods for common {service} clients (class-level introspection).",
                "parameters": {"type": "object", "properties": {}},
                "handler": _make_handler(candidates),
            }
        )
    return tools


def sdk_list_methods(client_path: str) -> Dict[str, Any]:
    cls = _resolve_client_class(client_path)
    return {"methods": _list_methods_of(cls)}

