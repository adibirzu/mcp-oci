"""
MCP Backend Auto-Discovery.

Scans directories for MCP servers and auto-generates BackendConfig entries.
Supports discovering servers from:

- .mcp.json files (standard MCP client config)
- pyproject.toml with [project.scripts] MCP entry points
- Python files containing FastMCP server instances
- Directories with known MCP server patterns

This enables the gateway to aggregate servers from different projects,
folders, and GitHub repos without manual configuration.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import structlog

from .config import BackendAuthMethod, BackendConfig, BackendTransport

logger = structlog.get_logger("oci-mcp.gateway.discovery")

# Filenames that indicate an MCP server project
MCP_CONFIG_FILES = (".mcp.json", "mcp.json")
PYPROJECT_FILE = "pyproject.toml"

# Pattern for FastMCP server in Python files
FASTMCP_PATTERNS = (
    "FastMCP(",
    "fastmcp.FastMCP(",
    "from fastmcp import FastMCP",
    "from mcp.server.fastmcp import FastMCP",
)


def discover_backends(
    scan_paths: list[str],
    *,
    recursive: bool = False,
    default_auth: BackendAuthMethod = BackendAuthMethod.NONE,
    default_tags: list[str] | None = None,
) -> list[BackendConfig]:
    """Scan directories for MCP servers and return BackendConfig entries.

    For each path in scan_paths, the discovery engine checks for:
    1. .mcp.json / mcp.json -- standard MCP client configs with mcpServers
    2. pyproject.toml -- projects with MCP-related entry points
    3. server.py / main.py -- Python files containing FastMCP instances

    Args:
        scan_paths: Directories or files to scan.
        recursive: If True, recurse one level into subdirectories.
        default_auth: Default auth method for discovered backends.
        default_tags: Default tags applied to discovered backends.

    Returns:
        List of auto-generated BackendConfig entries (disabled by default
        so the operator can review before enabling).
    """
    configs: list[BackendConfig] = []
    seen_names: set[str] = set()

    for scan_path in scan_paths:
        path = Path(scan_path).expanduser().resolve()
        if not path.exists():
            logger.warning("Scan path does not exist", path=str(path))
            continue

        if path.is_file():
            # Direct file -- check if it's a config or a server script
            found = _discover_from_file(path, default_auth, default_tags)
            for cfg in found:
                if cfg.name not in seen_names:
                    configs.append(cfg)
                    seen_names.add(cfg.name)
            continue

        # Directory -- check for MCP markers
        found = _discover_from_directory(path, default_auth, default_tags)
        for cfg in found:
            if cfg.name not in seen_names:
                configs.append(cfg)
                seen_names.add(cfg.name)

        # Recurse one level into subdirectories
        if recursive:
            for child in sorted(path.iterdir()):
                if child.is_dir() and not child.name.startswith("."):
                    found = _discover_from_directory(
                        child, default_auth, default_tags
                    )
                    for cfg in found:
                        if cfg.name not in seen_names:
                            configs.append(cfg)
                            seen_names.add(cfg.name)

    logger.info("Discovery complete", backends_found=len(configs))
    return configs


def discover_from_mcp_json(
    mcp_json_path: str | Path,
    *,
    default_auth: BackendAuthMethod = BackendAuthMethod.NONE,
    default_tags: list[str] | None = None,
) -> list[BackendConfig]:
    """Parse an .mcp.json file and convert its mcpServers to BackendConfigs.

    This handles the standard MCP client configuration format used by
    Claude Desktop, VS Code, and other MCP clients.

    Args:
        mcp_json_path: Path to .mcp.json file.
        default_auth: Default auth method for discovered backends.
        default_tags: Default tags applied to discovered backends.

    Returns:
        List of BackendConfig entries.
    """
    path = Path(mcp_json_path)
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to parse MCP config", path=str(path), error=str(e))
        return []

    servers = data.get("mcpServers", {})
    if not isinstance(servers, dict):
        return []

    configs: list[BackendConfig] = []
    project_dir = str(path.parent)

    for name, server_cfg in servers.items():
        if not isinstance(server_cfg, dict):
            continue

        config = _mcp_server_entry_to_backend(
            name=name,
            entry=server_cfg,
            project_dir=project_dir,
            default_auth=default_auth,
            tags=default_tags or [],
        )
        if config:
            configs.append(config)

    return configs


def load_backends_dir(backends_dir: str | Path) -> list[BackendConfig]:
    """Load all backend config fragments from a directory.

    Each *.json file in the directory should contain a single BackendConfig
    object (or a list of them). This allows operators to drop in backend
    definitions by file.

    Args:
        backends_dir: Directory containing *.json backend config files.

    Returns:
        List of BackendConfig entries loaded from the directory.
    """
    dirpath = Path(backends_dir).expanduser().resolve()
    if not dirpath.is_dir():
        logger.warning("Backends directory not found", path=str(dirpath))
        return []

    configs: list[BackendConfig] = []
    for json_file in sorted(dirpath.glob("*.json")):
        try:
            data = json.loads(json_file.read_text())
            if isinstance(data, list):
                for item in data:
                    configs.append(BackendConfig(**item))
            elif isinstance(data, dict):
                configs.append(BackendConfig(**data))
        except Exception as e:
            logger.warning(
                "Failed to load backend config",
                file=str(json_file),
                error=str(e),
            )

    logger.info(
        "Loaded backends from directory",
        dir=str(dirpath),
        count=len(configs),
    )
    return configs


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _discover_from_directory(
    dirpath: Path,
    default_auth: BackendAuthMethod,
    default_tags: list[str] | None,
) -> list[BackendConfig]:
    """Discover backends from a single directory."""
    configs: list[BackendConfig] = []

    # 1. Check for .mcp.json / mcp.json
    for mcp_file in MCP_CONFIG_FILES:
        mcp_path = dirpath / mcp_file
        if mcp_path.exists():
            found = discover_from_mcp_json(
                mcp_path,
                default_auth=default_auth,
                default_tags=default_tags,
            )
            configs.extend(found)
            if found:
                return configs  # .mcp.json is authoritative

    # 2. Check pyproject.toml for MCP entry points
    pyproject = dirpath / PYPROJECT_FILE
    if pyproject.exists():
        found = _discover_from_pyproject(
            pyproject, dirpath, default_auth, default_tags
        )
        configs.extend(found)
        if found:
            return configs

    # 3. Scan for Python files with FastMCP patterns
    for candidate in ("server.py", "main.py", "app.py"):
        script = dirpath / candidate
        if script.exists():
            cfg = _discover_from_python_file(
                script, dirpath, default_auth, default_tags
            )
            if cfg:
                configs.append(cfg)
                break  # Take the first match

    # 4. Check for src/ layout
    if not configs:
        src_dir = dirpath / "src"
        if src_dir.is_dir():
            for pkg in sorted(src_dir.iterdir()):
                if pkg.is_dir() and (pkg / "server.py").exists():
                    cfg = _discover_from_python_file(
                        pkg / "server.py", dirpath, default_auth,
                        default_tags,
                    )
                    if cfg:
                        configs.append(cfg)

    return configs


def _discover_from_file(
    filepath: Path,
    default_auth: BackendAuthMethod,
    default_tags: list[str] | None,
) -> list[BackendConfig]:
    """Discover backends from a single file."""
    if filepath.name in MCP_CONFIG_FILES:
        return discover_from_mcp_json(
            filepath, default_auth=default_auth, default_tags=default_tags
        )

    if filepath.suffix == ".json":
        # Try loading as a backend config fragment
        try:
            data = json.loads(filepath.read_text())
            if isinstance(data, dict) and "name" in data:
                return [BackendConfig(**data)]
        except Exception:
            pass

    if filepath.suffix == ".py":
        cfg = _discover_from_python_file(
            filepath, filepath.parent, default_auth, default_tags
        )
        return [cfg] if cfg else []

    return []


def _discover_from_pyproject(
    pyproject_path: Path,
    project_dir: Path,
    default_auth: BackendAuthMethod,
    default_tags: list[str] | None,
) -> list[BackendConfig]:
    """Discover MCP servers from a pyproject.toml."""
    try:
        # Use tomllib (stdlib in 3.11+)
        import tomllib
        data = tomllib.loads(pyproject_path.read_text())
    except Exception:
        return []

    configs: list[BackendConfig] = []
    project_name = data.get("project", {}).get("name", project_dir.name)
    scripts = data.get("project", {}).get("scripts", {})

    # Look for scripts that look like MCP server entry points
    for script_name, entry_point in scripts.items():
        is_mcp = any(
            hint in script_name.lower()
            for hint in ("mcp", "server", "gateway")
        )
        is_mcp = is_mcp or any(
            hint in entry_point.lower()
            for hint in ("mcp", "server", "fastmcp")
        )

        if not is_mcp:
            continue

        # Determine the command to run this server
        venv_python = _find_venv_python(project_dir)
        command = venv_python or sys.executable

        safe_name = _sanitize_name(f"{project_name}-{script_name}")
        tags = list(default_tags or [])
        tags.append("auto-discovered")
        tags.append(f"project:{project_name}")

        # Build PYTHONPATH that includes the project's src/ dir
        pythonpath_parts = _build_pythonpath(project_dir)

        env: dict[str, str] = {}
        if pythonpath_parts:
            env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

        configs.append(
            BackendConfig(
                name=safe_name,
                description=(
                    f"Auto-discovered from {project_dir.name}/pyproject.toml "
                    f"[{script_name}]"
                ),
                enabled=False,  # Disabled by default - operator must review
                transport=BackendTransport.STDIO,
                command=command,
                args=["-m", entry_point.split(":")[0]],
                cwd=str(project_dir),
                env=env,
                auth_method=default_auth,
                namespace_tools=True,
                tags=tags,
            )
        )

    return configs


def _discover_from_python_file(
    filepath: Path,
    project_dir: Path,
    default_auth: BackendAuthMethod,
    default_tags: list[str] | None,
) -> BackendConfig | None:
    """Check if a Python file contains a FastMCP server."""
    try:
        content = filepath.read_text(errors="ignore")
    except OSError:
        return None

    has_fastmcp = any(pattern in content for pattern in FASTMCP_PATTERNS)
    if not has_fastmcp:
        return None

    venv_python = _find_venv_python(project_dir)
    command = venv_python or sys.executable
    safe_name = _sanitize_name(project_dir.name)

    tags = list(default_tags or [])
    tags.append("auto-discovered")
    tags.append(f"file:{filepath.name}")

    pythonpath_parts = _build_pythonpath(project_dir)
    env: dict[str, str] = {}
    if pythonpath_parts:
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

    # Determine args - run the script directly or as a module
    script_rel = filepath.relative_to(project_dir)
    if str(script_rel).startswith("src/"):
        # Looks like a src-layout package, use -m
        module_path = str(script_rel).replace("/", ".").replace("\\", ".")
        if module_path.endswith(".py"):
            module_path = module_path[:-3]
        args = ["-m", module_path]
    else:
        args = [str(filepath)]

    return BackendConfig(
        name=safe_name,
        description=f"Auto-discovered from {project_dir.name}/{filepath.name}",
        enabled=False,  # Disabled by default
        transport=BackendTransport.STDIO,
        command=command,
        args=args,
        cwd=str(project_dir),
        env=env,
        auth_method=default_auth,
        namespace_tools=True,
        tags=tags,
    )


def _mcp_server_entry_to_backend(
    name: str,
    entry: dict[str, Any],
    project_dir: str,
    default_auth: BackendAuthMethod,
    tags: list[str],
) -> BackendConfig | None:
    """Convert a single .mcp.json mcpServers entry to a BackendConfig."""
    safe_name = _sanitize_name(name)

    # Determine transport type
    if "url" in entry:
        # Remote HTTP server
        return BackendConfig(
            name=safe_name,
            description=f"From .mcp.json [{name}] (HTTP)",
            enabled=False,
            transport=BackendTransport.STREAMABLE_HTTP,
            url=entry["url"],
            bearer_token=entry.get("headers", {}).get(
                "Authorization", ""
            ).removeprefix("Bearer ").strip() or None,
            auth_method=(
                BackendAuthMethod.BEARER_TOKEN
                if "headers" in entry
                else BackendAuthMethod.NONE
            ),
            namespace_tools=True,
            tags=[*tags, "auto-discovered", "mcp-json"],
        )

    if "command" in entry:
        # stdio server
        command = entry["command"]
        args = entry.get("args", [])
        env = entry.get("env", {})
        cwd = entry.get("cwd", project_dir)

        # Detect OCI auth from environment
        auth_method = default_auth
        if env.get("OCI_CLI_AUTH") == "resource_principal":
            auth_method = BackendAuthMethod.RESOURCE_PRINCIPAL
        elif env.get("OCI_CLI_AUTH") == "instance_principal":
            auth_method = BackendAuthMethod.INSTANCE_PRINCIPAL
        elif env.get("OCI_PROFILE") or env.get("OCI_CONFIG_FILE"):
            auth_method = BackendAuthMethod.OCI_CONFIG

        return BackendConfig(
            name=safe_name,
            description=f"From .mcp.json [{name}] (stdio)",
            enabled=False,
            transport=BackendTransport.STDIO,
            command=command,
            args=args,
            cwd=cwd,
            env=env,
            auth_method=auth_method,
            namespace_tools=True,
            tags=[*tags, "auto-discovered", "mcp-json"],
        )

    return None


def _find_venv_python(project_dir: Path) -> str | None:
    """Find a virtual environment Python binary in a project directory."""
    for venv_name in (".venv", "venv", ".env"):
        venv_dir = project_dir / venv_name
        if not venv_dir.is_dir():
            continue

        # Unix
        python = venv_dir / "bin" / "python"
        if python.exists():
            return str(python)

        # Windows
        python_win = venv_dir / "Scripts" / "python.exe"
        if python_win.exists():
            return str(python_win)

    return None


def _build_pythonpath(project_dir: Path) -> list[str]:
    """Build PYTHONPATH entries for a project directory."""
    paths: list[str] = []

    # src/ layout
    src = project_dir / "src"
    if src.is_dir():
        paths.append(str(src))

    # Project root
    paths.append(str(project_dir))

    return paths


def _sanitize_name(raw: str) -> str:
    """Sanitize a raw string into a valid backend name."""
    # Replace common separators
    name = raw.replace("/", "-").replace("\\", "-").replace(" ", "-")
    # Remove leading dots
    name = name.lstrip(".")
    # Collapse multiple hyphens
    while "--" in name:
        name = name.replace("--", "-")
    # Truncate
    name = name[:64].strip("-")
    return name or "unnamed"
