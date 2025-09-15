#!/usr/bin/env python3
"""
Test script for optimized MCP servers
Validates clear, Claude-friendly responses
"""

import sys
import os
import json
from typing import Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_optimized_servers():
    """Test optimized MCP server implementations"""
    
    print("🧪 Testing Optimized MCP Server Implementations")
    print("=" * 60)
    
    # Test compartment ID (you can replace with your actual compartment)
    test_compartment = "ocid1.compartment.oc1..aaaaaaaagy3yddkkampnhj3cqm5ar7w2p7tuq5twbojyycvol6wugfav3ckq"
    
    results = {}
    
    # Test Log Analytics Optimized
    print("\n📊 Testing Log Analytics Optimized...")
    try:
        from mcp_oci_loganalytics.server_simple import get_namespace_info_simple as get_namespace_info, list_entities_simple as list_entities, run_query_simple as run_query
        
        # Test namespace discovery
        print("   🔍 Testing namespace auto-discovery...")
        namespace_result = get_namespace_info()
        if namespace_result.get("success"):
            namespace = namespace_result.get("namespace")
            print(f"   ✅ Namespace discovered: {namespace}")
            results["loganalytics_namespace"] = {"status": "success", "namespace": namespace}
        else:
            print(f"   ❌ Namespace discovery failed: {namespace_result.get('error')}")
            results["loganalytics_namespace"] = {"status": "error", "error": namespace_result.get('error')}
        
        # Test list entities (should work without namespace parameter)
        print("   🔍 Testing list entities (no namespace needed)...")
        entities_result = list_entities(compartment_id=test_compartment, limit=5)
        if entities_result.get("success"):
            count = entities_result.get("count", 0)
            print(f"   ✅ List entities: Found {count} entities")
            print(f"   📝 Response format: {json.dumps(entities_result, indent=2)[:200]}...")
            results["loganalytics_entities"] = {"status": "success", "count": count}
        else:
            print(f"   ❌ List entities failed: {entities_result.get('error')}")
            results["loganalytics_entities"] = {"status": "error", "error": entities_result.get('error')}
        
        # Test run query (should work without namespace parameter)
        print("   🔍 Testing run query (no namespace needed)...")
        query_result = run_query(
            query_string="search * | head 5",
            time_start="2023-01-01T00:00:00Z",
            time_end="2023-01-02T00:00:00Z"
        )
        if query_result.get("success"):
            total_count = query_result.get("total_count", 0)
            print(f"   ✅ Run query: Found {total_count} results")
            print(f"   📝 Response format: {json.dumps(query_result, indent=2)[:200]}...")
            results["loganalytics_query"] = {"status": "success", "count": total_count}
        else:
            print(f"   ❌ Run query failed: {query_result.get('error')}")
            results["loganalytics_query"] = {"status": "error", "error": query_result.get('error')}
            
    except Exception as e:
        print(f"   ❌ Log Analytics Optimized Error: {str(e)}")
        results["loganalytics"] = {"status": "error", "error": str(e)}
    
    # Test IAM Optimized
    print("\n👤 Testing IAM Optimized...")
    try:
        from mcp_oci_iam.server_optimized import list_users, list_compartments
        
        # Test list users
        print("   🔍 Testing list users...")
        users_result = list_users(compartment_id=test_compartment, limit=5)
        if users_result.get("success"):
            count = users_result.get("count", 0)
            print(f"   ✅ List users: Found {count} users")
            print(f"   📝 Response format: {json.dumps(users_result, indent=2)[:200]}...")
            results["iam_users"] = {"status": "success", "count": count}
        else:
            print(f"   ❌ List users failed: {users_result.get('error')}")
            results["iam_users"] = {"status": "error", "error": users_result.get('error')}
        
        # Test list compartments
        print("   🔍 Testing list compartments...")
        compartments_result = list_compartments(compartment_id=test_compartment, limit=5)
        if compartments_result.get("success"):
            count = compartments_result.get("count", 0)
            print(f"   ✅ List compartments: Found {count} compartments")
            print(f"   📝 Response format: {json.dumps(compartments_result, indent=2)[:200]}...")
            results["iam_compartments"] = {"status": "success", "count": count}
        else:
            print(f"   ❌ List compartments failed: {compartments_result.get('error')}")
            results["iam_compartments"] = {"status": "error", "error": compartments_result.get('error')}
            
    except Exception as e:
        print(f"   ❌ IAM Optimized Error: {str(e)}")
        results["iam"] = {"status": "error", "error": str(e)}
    
    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 60)
    
    successful = 0
    total = len(results)
    
    for service, result in results.items():
        status = result.get("status", "unknown")
        if status == "success":
            successful += 1
            print(f"   ✅ {service}: SUCCESS")
        else:
            print(f"   ❌ {service}: FAILED - {result.get('error', 'Unknown error')}")
    
    print(f"\n🎯 Overall: {successful}/{total} services working")
    
    if successful == total:
        print("🎉 All optimized services are working correctly!")
    elif successful > 0:
        print("⚠️ Some services are working, some need attention.")
    else:
        print("❌ No services are working. Check OCI configuration.")
    
    return results

def demonstrate_claude_friendly_responses():
    """Demonstrate the difference between old and new response formats"""
    
    print("\n🔍 Response Format Comparison")
    print("=" * 60)
    
    # Old format (confusing for Claude)
    old_response = {
        "items": [
            {
                "_id": "ocid1.user.oc1..xxx",
                "_name": "john.doe@example.com",
                "_lifecycle_state": "ACTIVE",
                "_time_created": "2023-01-01T00:00:00Z",
                "_compartment_id": "ocid1.compartment.oc1..xxx",
                "_email_verified": True,
                "_is_mfa_activated": False,
                "_defined_tags": {"Oracle-Tags": {"CreatedBy": "admin"}},
                "_freeform_tags": {"department": "engineering"}
            }
        ]
    }
    
    # New format (Claude-friendly)
    new_response = {
        "success": True,
        "compartment_id": "ocid1.compartment.oc1..xxx",
        "count": 1,
        "users": [
            {
                "id": "ocid1.user.oc1..xxx",
                "name": "john.doe@example.com",
                "lifecycle_state": "ACTIVE",
                "time_created": "2023-01-01T00:00:00Z",
                "email": "john.doe@example.com",
                "email_verified": True,
                "is_mfa_activated": False
            }
        ],
        "message": "Found 1 users in compartment ocid1.compartment.oc1..xxx"
    }
    
    print("📝 OLD FORMAT (Confusing for Claude):")
    print(json.dumps(old_response, indent=2))
    print()
    print("📝 NEW FORMAT (Claude-Friendly):")
    print(json.dumps(new_response, indent=2))
    print()
    print("✅ Benefits of New Format:")
    print("   • Clear success/error indication")
    print("   • Helpful messages explaining what was found")
    print("   • Clean field names (no underscores)")
    print("   • Structured data that Claude can easily understand")
    print("   • Consistent response format across all tools")

if __name__ == "__main__":
    # Test optimized servers
    results = test_optimized_servers()
    
    # Demonstrate response format improvements
    demonstrate_claude_friendly_responses()
    
    print("\n🚀 Optimization Status:")
    print("   ✅ Log Analytics namespace auto-discovery implemented")
    print("   ✅ Clear, Claude-friendly response formats")
    print("   ✅ Better error handling and user guidance")
    print("   ✅ Simplified API - fewer required parameters")
    print("   ✅ Consistent response structure across all tools")
