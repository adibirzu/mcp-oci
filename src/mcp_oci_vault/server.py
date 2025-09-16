"""MCP Server: OCI Vault (Secrets)
"""

from typing import Any

from mcp_oci_common import make_client
from mcp_oci_common.response import with_meta

try:
    import oci  # type: ignore
except Exception:
    oci = None


def create_client(profile: str | None = None, region: str | None = None):
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    return make_client(oci.secrets.SecretsClient, profile=profile, region=region)


def register_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "oci:vault:list-secrets",
            "description": "List secrets in a compartment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"}
                },
                "required": ["compartment_id"],
            },
            "handler": list_secrets,
        },
        {
            "name": "oci:vault:get-secret-bundle",
            "description": "Get latest secret bundle.",
            "parameters": {
                "type": "object",
                "properties": {
                    "secret_id": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"}
                },
                "required": ["secret_id"],
            },
            "handler": get_secret_bundle,
        }
    ]


def list_secrets(compartment_id: str, limit: int | None = None, page: str | None = None,
                 profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    cfg = oci.config.from_file(profile_name=profile)
    if region:
        cfg["region"] = region
    vc = oci.vault.VaultsClient(cfg)
    kwargs: dict[str, Any] = {}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = vc.list_secrets(compartment_id=compartment_id, **kwargs)
    items = [s.__dict__ for s in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def get_secret_bundle(secret_id: str, profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    resp = client.get_secret_bundle(secret_id)
    data = getattr(resp, "data", None)
    return with_meta(resp, {"item": getattr(data, "__dict__", data)})
