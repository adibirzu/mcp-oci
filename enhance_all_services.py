#!/usr/bin/env python3
"""
Script to enhance all MCP services with better OCI API calls and fallback mechanisms
"""
import os
import glob
import re

def enhance_service_file(file_path):
    """Enhance a single service file with better API calls"""
    print(f"Enhancing {file_path}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Skip if already enhanced
    if "fallback_reason" in content or "method" in content:
        print(f"  ⏭️  Already enhanced: {file_path}")
        return False
    
    # Add enhanced error handling and fallback mechanisms
    enhancements = [
        # Add try-catch blocks around API calls
        (r'(\s+)(resp = client\.\w+\([^)]+\))', r'\1try:\n\1    \2\n\1except Exception as e:\n\1    return _handle_api_error(e, str(e))'),
        
        # Add fallback methods
        (r'def (\w+)\([^)]*\) -> Dict\[str, Any\]:', r'def \1(\1_params) -> Dict[str, Any]:\n    """Enhanced with fallback mechanisms"""\n    try:\n        return _call_primary_api(\1_params)\n    except Exception as e:\n        return _fallback_api_call(\1_params, str(e))'),
    ]
    
    # Apply enhancements
    modified = False
    for pattern, replacement in enhancements:
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        if new_content != content:
            content = new_content
            modified = True
    
    if modified:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"  ✅ Enhanced: {file_path}")
        return True
    else:
        print(f"  ⏭️  No changes needed: {file_path}")
        return False

def main():
    """Enhance all service files"""
    service_dir = "src/mcp_oci_fastmcp"
    files = glob.glob(f"{service_dir}/*.py")
    
    enhanced_count = 0
    for file_path in files:
        if file_path.endswith("__init__.py") or file_path.endswith("__main__.py"):
            continue
        if enhance_service_file(file_path):
            enhanced_count += 1
    
    print(f"\n✅ Enhanced {enhanced_count} service files")

if __name__ == "__main__":
    main()
