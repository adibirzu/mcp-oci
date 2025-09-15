import argparse
import importlib
import json
from typing import Any, Dict

SERVICES = [
    "iam","compute","objectstorage","networking","blockstorage","loadbalancer",
    "filestorage","dns","apigateway","database","oke","functions","logging",
    "monitoring","events","streaming","ons","vault","kms","resourcemanager",
]


def load_service(service: str):
    mod = importlib.import_module(f"mcp_oci_{service}.server")
    return mod


def cmd_list_tools(args: argparse.Namespace) -> None:
    mod = load_service(args.service)
    tools = getattr(mod, "register_tools")()
    print(json.dumps([{"name": t["name"], "description": t.get("description", "")} for t in tools], indent=2))


def cmd_call(args: argparse.Namespace) -> None:
    mod = load_service(args.service)
    tools = {t["name"]: t for t in getattr(mod, "register_tools")()}
    tool = tools.get(args.name)
    if not tool:
        raise SystemExit(f"Tool not found: {args.name}")
    handler = tool.get("handler")
    if not handler:
        raise SystemExit("Tool has no handler bound.")
    params: Dict[str, Any] = json.loads(args.params) if args.params else {}
    result = handler(**params)
    print(json.dumps(result, indent=2, default=str))


def main() -> None:
    p = argparse.ArgumentParser(prog="mcp-oci", description="MCP OCI dev CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    lp = sub.add_parser("list-tools", help="List tools for a service")
    lp.add_argument("service", choices=SERVICES)
    lp.set_defaults(func=cmd_list_tools)

    cp = sub.add_parser("call", help="Call a tool handler (dev)")
    cp.add_argument("service", choices=SERVICES)
    cp.add_argument("name", help="Tool name, e.g., oci:iam:list-users")
    cp.add_argument("--params", default="{}", help="JSON object of parameters")
    cp.set_defaults(func=cmd_call)

    dp = sub.add_parser("doctor", help="Check OCI SDK/config connectivity")
    dp.add_argument("--profile")
    dp.add_argument("--region")
    dp.set_defaults(func=cmd_doctor)

    args = p.parse_args()
    args.func(args)


def cmd_doctor(args: argparse.Namespace) -> None:
    try:
        import oci  # type: ignore
    except Exception as e:  # pragma: no cover
        raise SystemExit(f"OCI SDK not installed: {e}")
    profile = args.profile or "DEFAULT"
    region = args.region
    try:
        cfg = oci.config.from_file(profile_name=profile)
        if region:
            cfg["region"] = region
        client = oci.identity.IdentityClient(cfg)
        resp = client.list_regions()
        regions = [r.key for r in getattr(resp, "data", [])]
        print(json.dumps({
            "status": "ok",
            "profile": profile or cfg.get("profile", "DEFAULT"),
            "region": cfg.get("region"),
            "tenancy": cfg.get("tenancy"),
            "regions_available": regions,
        }, indent=2))
    except Exception as e:
        raise SystemExit(f"Doctor check failed: {e}")


if __name__ == "__main__":
    main()
