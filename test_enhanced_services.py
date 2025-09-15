#!/usr/bin/env python3
"""
Test enhanced MCP services with better error handling and API calls
"""
import asyncio
import json
import subprocess
import sys

async def test_service(service_name, test_cases):
    """Test a specific service with multiple test cases"""
    print(f"\n🔍 Testing {service_name} service...")
    
    # Start the MCP server
    process = subprocess.Popen(
        ["/Users/abirzu/.pyenv/versions/3.11.9/bin/python", "-m", "mcp_oci_fastmcp", 
         service_name, "--profile", "DEFAULT", "--region", "eu-frankfurt-1"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Wait for server to start
        await asyncio.sleep(3)
        
        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        
        # Read initialize response
        response_line = process.stdout.readline()
        init_response = json.loads(response_line.strip())
        print(f"✅ {service_name} initialized: {init_response.get('result', {}).get('serverInfo', {})}")
        
        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        process.stdin.write(json.dumps(initialized_notification) + "\n")
        process.stdin.flush()
        
        # Run test cases
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n  Test {i}: {test_case['description']}")
            
            tool_request = {
                "jsonrpc": "2.0",
                "id": i + 1,
                "method": "tools/call",
                "params": {
                    "name": test_case["tool"],
                    "arguments": test_case["arguments"]
                }
            }
            
            process.stdin.write(json.dumps(tool_request) + "\n")
            process.stdin.flush()
            
            response_line = process.stdout.readline()
            tool_response = json.loads(response_line.strip())
            
            if "error" in tool_response:
                print(f"    ❌ Failed: {tool_response['error']}")
            else:
                result = tool_response.get("result", {})
                if result.get("isError"):
                    print(f"    ❌ OCI API error: {result.get('content', [{}])[0].get('text', 'Unknown error')}")
                else:
                    print(f"    ✅ Success!")
                    content = result.get("content", [{}])[0].get("text", "{}")
                    try:
                        data = json.loads(content)
                        items = data.get("items", [])
                        print(f"    📊 Found {len(items)} items")
                        
                        # Check for enhanced features
                        if "hints" in data:
                            print(f"    💡 Hints provided: {data['hints'].get('message', 'No message')}")
                        if "fallback_reason" in data:
                            print(f"    🔄 Used fallback: {data.get('method', 'Unknown')}")
                        if "query" in data:
                            print(f"    🔍 Query used: {data['query']}")
                            
                    except Exception as e:
                        print(f"    ⚠️  Could not parse response: {e}")
        
    except Exception as e:
        print(f"❌ {service_name} test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        process.terminate()
        process.wait()

async def main():
    """Run comprehensive tests for all enhanced services"""
    print("🚀 Testing Enhanced MCP OCI Services")
    print("=" * 50)
    
    # Test cases for different services
    test_suites = {
        "compute": [
            {
                "description": "Enhanced search with multiple lifecycle states",
                "tool": "oci_compute_search_instances",
                "arguments": {
                    "query": "lifecycle_state:RUNNING OR lifecycle_state:STARTING OR lifecycle_state:PROVISIONING OR lifecycle_state:PENDING",
                    "compartment_id": "ocid1.tenancy.oc1..aaaaaaaagy3yddkkampnhj3cqm5ar7w2p7tuq5twbojyycvol6wugfav3ckq",
                    "include_subtree": True
                }
            },
            {
                "description": "Simple search with single lifecycle state",
                "tool": "oci_compute_search_instances",
                "arguments": {
                    "lifecycle_state": "RUNNING",
                    "compartment_id": "ocid1.tenancy.oc1..aaaaaaaagy3yddkkampnhj3cqm5ar7w2p7tuq5twbojyycvol6wugfav3ckq",
                    "include_subtree": True
                }
            },
            {
                "description": "Regular list instances (fallback method)",
                "tool": "oci_compute_list_instances",
                "arguments": {
                    "compartment_id": "ocid1.tenancy.oc1..aaaaaaaagy3yddkkampnhj3cqm5ar7w2p7tuq5twbojyycvol6wugfav3ckq",
                    "lifecycle_state": "RUNNING",
                    "include_subtree": True
                }
            }
        ],
        "iam": [
            {
                "description": "List compartments with enhanced error handling",
                "tool": "oci_iam_list_compartments",
                "arguments": {
                    "compartment_id": "ocid1.tenancy.oc1..aaaaaaaagy3yddkkampnhj3cqm5ar7w2p7tuq5twbojyycvol6wugfav3ckq",
                    "include_subtree": True
                }
            },
            {
                "description": "List users with helpful hints",
                "tool": "oci_iam_list_users",
                "arguments": {
                    "compartment_id": "ocid1.tenancy.oc1..aaaaaaaagy3yddkkampnhj3cqm5ar7w2p7tuq5twbojyycvol6wugfav3ckq"
                }
            }
        ],
        "monitoring": [
            {
                "description": "List metrics with enhanced error handling",
                "tool": "oci_monitoring_list_metrics",
                "arguments": {
                    "compartment_id": "ocid1.tenancy.oc1..aaaaaaaagy3yddkkampnhj3cqm5ar7w2p7tuq5twbojyycvol6wugfav3ckq"
                }
            }
        ]
    }
    
    # Run tests for each service
    for service_name, test_cases in test_suites.items():
        await test_service(service_name, test_cases)
    
    print("\n🎉 Enhanced MCP Services Testing Complete!")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
