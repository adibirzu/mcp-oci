"""
MCP Gateway - Module Entry Point.

Allows running the gateway as a Python module:
    python -m mcp_server_oci.gateway
    python -m mcp_server_oci.gateway --config gateway.json
    python -m mcp_server_oci.gateway --port 9000 --host 0.0.0.0
"""
from __future__ import annotations

import argparse
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
  python -m mcp_server_oci.gateway --config gateway.json

  # Run with environment overrides
  MCP_GATEWAY_PORT=8080 python -m mcp_server_oci.gateway

  # Run with CLI overrides
  python -m mcp_server_oci.gateway --port 8080 --host 127.0.0.1 --no-auth

  # Run with the local OCI MCP server as in-process backend
  python -m mcp_server_oci.gateway --config gateway.json --log-level DEBUG
""",
    )

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

    try:
        run_gateway(config)
    except KeyboardInterrupt:
        print("\nGateway stopped.", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
