# OCI SDK Introspection Server

Exposes generic and service-specific tools to list available SDK methods, useful when new SDK versions add capabilities.

## Tools
- `oci:sdk:list-methods` — List methods for a specific client class. Param: `client_path` (e.g., `monitoring.MonitoringClient`).
- `oci:<service>:list-sdk-methods` — Service-specific helpers for common clients; available for identity, compute, networking, blockstorage, objectstorage, monitoring, loganalytics, usageapi, budgets, limits, dns, loadbalancer, filestorage, apigateway, database, oke, functions, events, streaming, ons, vault, kms, resourcemanager, osub.

## Usage
Serve:
```
mcp-oci-serve-introspect
```
Examples:
```
mcp-oci call introspect oci:sdk:list-methods --params '{"client_path":"monitoring.MonitoringClient"}'
mcp-oci call introspect oci:monitoring:list-sdk-methods
```

## Notes
- Introspection is class-level; methods available only at instance-level might not appear.
- Use `list-sdk-methods` to detect newer SDK methods and update your workflows/tools accordingly.
