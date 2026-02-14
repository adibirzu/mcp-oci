"""
MCP Gateway - Module Entry Point.

Allows running the gateway as a Python module:
    python -m mcp_server_oci.gateway
    python -m mcp_server_oci.gateway --config gateway.json
    python -m mcp_server_oci.gateway --port 9000 --host 0.0.0.0
    python -m mcp_server_oci.gateway --scan /path/to/projects
    python -m mcp_server_oci.gateway --backends-dir ./backends.d
"""
from __future__ import annotations

import argparse
import json
import sys

from .config import load_gateway_config
from .server import run_gateway


def main() -> None:
    """CLI entry point for the MCP Gateway."""
    parser = argparse.ArgumentParser(
        description="MCP Gateway - Aggregating proxy for multiple MCP servers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with configuration file
  oci-mcp-gateway --config gateway.json

  # Run with environment overrides
  MCP_GATEWAY_PORT=8080 oci-mcp-gateway

  # Run with CLI overrides
  oci-mcp-gateway --port 8080 --host 127.0.0.1 --no-auth

  # Scan a directory tree for MCP servers
  oci-mcp-gateway --scan ~/projects --scan ~/work/mcp-servers

  # Load backend configs from a drop-in directory
  oci-mcp-gateway --backends-dir ./backends.d

  # Discover backends and print what was found (dry run)
  oci-mcp-gateway --scan ~/projects --discover-only

  # Run with the local OCI MCP server as in-process backend
  oci-mcp-gateway --config gateway.json --log-level DEBUG
""",
    )

    # -- Core options --
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="Path to gateway configuration JSON file",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Listen address (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=None,
        help="Listen port (default: 9000)",
    )
    parser.add_argument(
        "--path",
        type=str,
        default=None,
        help="MCP endpoint path (default: /mcp)",
    )
    parser.add_argument(
        "--no-auth",
        action="store_true",
        default=False,
        help="Disable authentication (development only)",
    )
    parser.add_argument(
        "--stateless",
        action="store_true",
        default=False,
        help="Run in stateless mode for horizontal scaling",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)",
    )

    # -- Discovery & multi-project options --
    parser.add_argument(
        "--scan",
        type=str,
        action="append",
        default=None,
        metavar="DIR",
        help=(
            "Scan a directory for MCP servers (repeatable). "
            "Discovered backends are added as disabled for review."
        ),
    )
    parser.add_argument(
        "--backends-dir",
        type=str,
        default=None,
        metavar="DIR",
        help="Load backend config fragments from *.json files in this directory",
    )
    parser.add_argument(
        "--discover-only",
        action="store_true",
        default=False,
        help=(
            "Print discovered backends as JSON and exit without "
            "starting the server. Useful for generating config."
        ),
    )

    args = parser.parse_args()

    # Load base config
    config = load_gateway_config(args.config)

    # Apply CLI overrides
    if args.host is not None:
        config.host = args.host
    if args.port is not None:
        config.port = args.port
    if args.path is not None:
        config.path = args.path
    if args.no_auth:
        config.auth.enabled = False
    if args.stateless:
        config.stateless = True
    if args.log_level is not None:
        config.log_level = args.log_level

    # Merge --backends-dir
    if args.backends_dir:
        config.backends_dir = args.backends_dir
        from .discovery import load_backends_dir

        seen = {b.name for b in config.backends}
        for b in load_backends_dir(args.backends_dir):
            if b.name not in seen:
                config.backends.append(b)
                seen.add(b.name)

    # Merge --scan paths
    if args.scan:
        from .discovery import discover_backends

        seen = {b.name for b in config.backends}
        for b in discover_backends(args.scan, recursive=True):
            if b.name not in seen:
                config.backends.append(b)
                seen.add(b.name)

    # --discover-only: print and exit
    if args.discover_only:
        _print_discovered(config)
        sys.exit(0)

    try:
        run_gateway(config)
    except KeyboardInterrupt:
        print("\nGateway stopped.", file=sys.stderr)
        sys.exit(0)


def _print_discovered(config) -> None:  # noqa: ANN001
    """Print all discovered backends as JSON for review."""
    backends_data = []
    for b in config.backends:
        entry = b.model_dump(mode="json", exclude_defaults=True)
        # Always include these key fields
        entry["name"] = b.name
        entry["enabled"] = b.enabled
        entry["transport"] = b.transport.value
        backends_data.append(entry)

    output = {
        "backends": backends_data,
        "summary": {
            "total": len(backends_data),
            "enabled": sum(1 for b in config.backends if b.enabled),
            "disabled": sum(1 for b in config.backends if not b.enabled),
            "by_transport": {
                "stdio": sum(
                    1 for b in config.backends if b.transport == "stdio"
                ),
                "streamable_http": sum(
                    1 for b in config.backends
                    if b.transport == "streamable_http"
                ),
                "in_process": sum(
                    1 for b in config.backends
                    if b.transport == "in_process"
                ),
            },
        },
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
