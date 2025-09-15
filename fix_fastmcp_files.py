#!/usr/bin/env python3
"""
Script to fix all FastMCP files to use manual args dict instead of locals()
"""
import os
import re
import glob

def fix_fastmcp_file(file_path):
    """Fix a single FastMCP file"""
    print(f"Fixing {file_path}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find all function definitions that use locals()
    pattern = r'@app\.tool\(\)\s+async def (\w+)\((.*?)\):\s+return (\w+)\(\*\*_with_defaults\(locals\(\)\)\)'
    
    def replace_function(match):
        func_name = match.group(1)
        params = match.group(2)
        call_func = match.group(3)
        
        # Parse parameters
        param_lines = []
        for param in params.split(','):
            param = param.strip()
            if '=' in param:
                param_name = param.split('=')[0].strip()
                param_lines.append(f'            "{param_name}": {param_name},')
            else:
                param_lines.append(f'            "{param}": {param},')
        
        # Build the replacement
        replacement = f"""@app.tool()
    async def {func_name}({params}):
        args = {{
{chr(10).join(param_lines)}
        }}
        args = _with_defaults(args)
        return {call_func}(**args)"""
        
        return replacement
    
    # Apply the replacement
    new_content = re.sub(pattern, replace_function, content, flags=re.DOTALL)
    
    # Write back if changed
    if new_content != content:
        with open(file_path, 'w') as f:
            f.write(new_content)
        print(f"  ✅ Fixed {file_path}")
        return True
    else:
        print(f"  ⏭️  No changes needed for {file_path}")
        return False

def main():
    """Fix all FastMCP files"""
    fastmcp_dir = "src/mcp_oci_fastmcp"
    files = glob.glob(f"{fastmcp_dir}/*.py")
    
    fixed_count = 0
    for file_path in files:
        if file_path.endswith("__init__.py") or file_path.endswith("__main__.py"):
            continue
        if fix_fastmcp_file(file_path):
            fixed_count += 1
    
    print(f"\n✅ Fixed {fixed_count} files")

if __name__ == "__main__":
    main()
