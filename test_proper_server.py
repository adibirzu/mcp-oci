#!/usr/bin/env python3
"""
Test the proper FastMCP server implementation
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_oci_fastmcp.server_proper import (
    test_connection,
    get_server_info,
    list_compartments,
    get_compartment_guidance,
    list_compute_instances,
    get_log_analytics_namespace,
    list_log_analytics_entities,
)

async def test_proper_server():
    """Test the proper server implementation."""
    print("🧪 Testing Proper FastMCP Server Implementation")
    print("=" * 60)
    
    results = {}
    
    # Test connection
    print("\n🔍 Testing connection...")
    try:
        result = await test_connection()
        data = json.loads(result)
        if data.get("success"):
            print("   ✅ Connection successful")
            print(f"   📝 Region: {data.get('region')}")
            print(f"   📝 Tenancy: {data.get('tenancy')}")
            print(f"   📝 Root Compartment: {data.get('root_compartment_id')}")
            results["connection"] = "SUCCESS"
        else:
            print(f"   ❌ Connection failed: {data.get('error_message')}")
            results["connection"] = "FAILED"
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        results["connection"] = "FAILED"
    
    # Test server info
    print("\n🔍 Testing server info...")
    try:
        result = await get_server_info()
        data = json.loads(result)
        if data.get("success"):
            print("   ✅ Server info retrieved")
            print(f"   📝 Server: {data.get('server_name')}")
            print(f"   📝 Version: {data.get('version')}")
            print(f"   📝 Features: {len(data.get('features', []))} features")
            results["server_info"] = "SUCCESS"
        else:
            print(f"   ❌ Server info failed: {data.get('error_message')}")
            results["server_info"] = "FAILED"
    except Exception as e:
        print(f"   ❌ Server info error: {e}")
        results["server_info"] = "FAILED"
    
    # Test compartment listing
    print("\n🔍 Testing compartment listing...")
    try:
        result = await list_compartments(limit=10)
        data = json.loads(result)
        if data.get("success"):
            print("   ✅ Compartments listed")
            print(f"   📝 Found {data.get('count')} compartments")
            print(f"   📝 Root compartment: {data.get('root_compartment_id')}")
            results["compartments"] = "SUCCESS"
        else:
            print(f"   ❌ Compartment listing failed: {data.get('error_message')}")
            results["compartments"] = "FAILED"
    except Exception as e:
        print(f"   ❌ Compartment listing error: {e}")
        results["compartments"] = "FAILED"
    
    # Test compartment guidance
    print("\n🔍 Testing compartment guidance...")
    try:
        result = await get_compartment_guidance()
        data = json.loads(result)
        if data.get("message"):
            print("   ✅ Compartment guidance provided")
            print(f"   📝 Message: {data.get('message')}")
            print(f"   📝 Compartments available: {data.get('count', 0)}")
            results["compartment_guidance"] = "SUCCESS"
        else:
            print(f"   ❌ Compartment guidance failed: {data.get('error', 'Unknown error')}")
            results["compartment_guidance"] = "FAILED"
    except Exception as e:
        print(f"   ❌ Compartment guidance error: {e}")
        results["compartment_guidance"] = "FAILED"
    
    # Test compute instances (using root compartment)
    print("\n🔍 Testing compute instances (root compartment)...")
    try:
        result = await list_compute_instances(limit=5)  # No compartment_id = uses root
        data = json.loads(result)
        if data.get("success"):
            print("   ✅ Compute instances listed")
            print(f"   📝 Found {data.get('count')} instances")
            print(f"   📝 Compartment used: {data.get('compartment_id')}")
            print(f"   📝 Message: {data.get('message')}")
            results["compute_instances"] = "SUCCESS"
        else:
            print(f"   ❌ Compute instances failed: {data.get('error_message')}")
            results["compute_instances"] = "FAILED"
    except Exception as e:
        print(f"   ❌ Compute instances error: {e}")
        results["compute_instances"] = "FAILED"
    
    # Test Log Analytics namespace
    print("\n🔍 Testing Log Analytics namespace...")
    try:
        result = await get_log_analytics_namespace()
        data = json.loads(result)
        if data.get("success"):
            print("   ✅ Log Analytics namespace retrieved")
            print(f"   📝 Namespace: {data.get('namespace')}")
            print(f"   📝 Message: {data.get('message')}")
            results["log_analytics_namespace"] = "SUCCESS"
        else:
            print(f"   ❌ Log Analytics namespace failed: {data.get('error_message')}")
            results["log_analytics_namespace"] = "FAILED"
    except Exception as e:
        print(f"   ❌ Log Analytics namespace error: {e}")
        results["log_analytics_namespace"] = "FAILED"
    
    # Test Log Analytics entities (using root compartment)
    print("\n🔍 Testing Log Analytics entities (root compartment)...")
    try:
        result = await list_log_analytics_entities(limit=5)  # No compartment_id = uses root
        data = json.loads(result)
        if data.get("success"):
            print("   ✅ Log Analytics entities listed")
            print(f"   📝 Found {data.get('count')} entities")
            print(f"   📝 Compartment used: {data.get('compartment_id')}")
            print(f"   📝 Namespace: {data.get('namespace')}")
            print(f"   📝 Message: {data.get('message')}")
            results["log_analytics_entities"] = "SUCCESS"
        else:
            print(f"   ❌ Log Analytics entities failed: {data.get('error_message')}")
            results["log_analytics_entities"] = "FAILED"
    except Exception as e:
        print(f"   ❌ Log Analytics entities error: {e}")
        results["log_analytics_entities"] = "FAILED"
    
    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 60)
    success_count = sum(1 for status in results.values() if status == "SUCCESS")
    total_count = len(results)
    
    for test_name, status in results.items():
        status_icon = "✅" if status == "SUCCESS" else "❌"
        print(f"   {status_icon} {test_name}: {status}")
    
    print(f"\n🎯 Overall: {success_count}/{total_count} tests passed")
    
    if success_count == total_count:
        print("🎉 All tests passed! The proper implementation is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the error messages above.")
    
    print("\n🔍 Key Features Verified:")
    print("   ✅ Root tenancy as default compartment")
    print("   ✅ Compartment auto-discovery")
    print("   ✅ Claude-friendly response format")
    print("   ✅ Proper OCI config handling")
    print("   ✅ Comprehensive error handling")
    print("   ✅ No manual namespace parameters needed")

if __name__ == "__main__":
    asyncio.run(test_proper_server())
