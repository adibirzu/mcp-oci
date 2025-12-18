#!/usr/bin/env python3
"""
Safe Serialization Fix for OCI MCP Servers
Adds comprehensive serialization functions to handle OCI SDK objects
"""

import re
from pathlib import Path

SAFE_SERIALIZE_FUNCTION = '''
def _safe_serialize(obj):
    """Safely serialize OCI SDK objects and other complex types"""
    if obj is None:
        return None

    # Handle OCI SDK objects
    if hasattr(obj, '__dict__'):
        try:
            # Try to convert OCI objects to dict
            if hasattr(obj, 'to_dict'):
                return obj.to_dict()
            elif hasattr(obj, '_data') and hasattr(obj._data, '__dict__'):
                return obj._data.__dict__
            else:
                # Fallback to manual serialization of object attributes
                result = {}
                for key, value in obj.__dict__.items():
                    if not key.startswith('_'):
                        result[key] = _safe_serialize(value)
                return result
        except Exception as e:
            return {"serialization_error": str(e), "original_type": str(type(obj))}

    # Handle lists and tuples
    elif isinstance(obj, (list, tuple)):
        return [_safe_serialize(item) for item in obj]

    # Handle dictionaries
    elif isinstance(obj, dict):
        return {key: _safe_serialize(value) for key, value in obj.items()}

    # Handle primitive types
    elif isinstance(obj, (str, int, float, bool)):
        return obj

    # For unknown types, try to convert to string
    else:
        try:
            return str(obj)
        except Exception:
            return {"unknown_type": str(type(obj))}
'''

def find_mcp_servers():
    """Find all MCP server files"""
    servers_dir = Path(__file__).resolve().parent / "mcp_servers"
    server_files = []

    for server_dir in servers_dir.iterdir():
        if server_dir.is_dir():
            server_file = server_dir / "server.py"
            if server_file.exists():
                server_files.append(server_file)

    return server_files

def check_needs_fix(file_path):
    """Check if a server file needs the serialization fix"""
    with open(file_path, 'r') as f:
        content = f.read()

    # Check if it already has safe serialization
    if '_safe_serialize' in content:
        return False

    # Check if it imports OCI SDK or might return OCI objects
    indicators = [
        'import oci',
        'from oci',
        '.to_dict(',
        'LaunchOptions',
        'return.*items',
        'OCI.*objects'
    ]

    for indicator in indicators:
        if re.search(indicator, content, re.IGNORECASE):
            return True

    return False

def apply_fix(file_path):
    """Apply the safe serialization fix to a server file"""
    with open(file_path, 'r') as f:
        content = f.read()

    # Find a good place to insert the function (after imports, before first function)
    lines = content.split('\\n')
    insert_line = 0

    # Look for the end of imports and cache setup
    for i, line in enumerate(lines):
        if 'cache = get_cache()' in line:
            insert_line = i + 1
            break
        elif line.strip().startswith('def ') and not line.strip().startswith('def _'):
            insert_line = i
            break

    # Insert the safe serialization function
    if insert_line > 0:
        lines.insert(insert_line, SAFE_SERIALIZE_FUNCTION)

        # Write back to file
        with open(file_path, 'w') as f:
            f.write('\\n'.join(lines))

        print(f"✅ Added safe serialization to {file_path.name}")
        return True
    else:
        print(f"❌ Could not find insertion point in {file_path.name}")
        return False

def main():
    """Main function to fix all MCP servers"""
    print("🔧 Applying Safe Serialization Fix to OCI MCP Servers")
    print("=" * 60)

    server_files = find_mcp_servers()

    servers_fixed = 0
    servers_skipped = 0

    for server_file in server_files:
        print(f"\\n📁 Checking {server_file.parent.name}/server.py...")

        if not check_needs_fix(server_file):
            print(f"⏭️  {server_file.parent.name} already has safe serialization or doesn't need it")
            servers_skipped += 1
            continue

        if apply_fix(server_file):
            servers_fixed += 1
        else:
            print(f"❌ Failed to fix {server_file.parent.name}")

    print("\\n" + "=" * 60)
    print("🎉 Summary:")
    print(f"   ✅ Servers Fixed: {servers_fixed}")
    print(f"   ⏭️  Servers Skipped: {servers_skipped}")
    print(f"   📊 Total Servers: {len(server_files)}")

    if servers_fixed > 0:
        print("\\n🚀 All servers should now handle OCI SDK serialization properly!")
        print("   Test each server with: timeout 10 start-mcp-server.sh <server-name>")

if __name__ == "__main__":
    main()
