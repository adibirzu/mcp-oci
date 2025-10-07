from mcp_oci_runtime.stdio import run_with_tools
from mcp_oci_vault.server import register_tools


def main() -> None:
    run_with_tools(register_tools())


if __name__ == "__main__":
    main()
