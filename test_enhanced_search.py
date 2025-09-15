#!/usr/bin/env python3
"""
Test enhanced search functionality with proper OCI query syntax
"""
import asyncio
import json
import subprocess
import sys

async def test_enhanced_search():
    """Test the enhanced search functionality"""
    print("🔍 Testing enhanced OCI search functionality...")
    
    # Start the MCP server
    process = subprocess.Popen(
        ["/Users/abirzu/.pyenv/versions/3.11.9/bin/python", "-m", "mcp_oci_fastmcp", 
         "compute", "--profile", "DEFAULT", "--region", "eu-frankfurt-1"],
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
        print(f"✅ Server initialized: {init_response.get('result', {}).get('serverInfo', {})}")
        
        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        process.stdin.write(json.dumps(initialized_notification) + "\n")
        process.stdin.flush()
        
        # Test 1: Enhanced search with multiple lifecycle states
        print("\n🔍 Test 1: Enhanced search with multiple lifecycle states...")
        tool_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "oci_compute_search_instances",
                "arguments": {
                    "query": "lifecycle_state:RUNNING OR lifecycle_state:STARTING OR lifecycle_state:PROVISIONING OR lifecycle_state:PENDING",
                    "compartment_id": "ocid1.tenancy.oc1..aaaaaaaagy3yddkkampnhj3cqm5ar7w2p7tuq5twbojyycvol6wugfav3ckq",
                    "include_subtree": True
                }
            }
        }
        
        process.stdin.write(json.dumps(tool_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        tool_response = json.loads(response_line.strip())
        
        if "error" in tool_response:
            print(f"❌ Test 1 failed: {tool_response['error']}")
        else:
            result = tool_response.get("result", {})
            if result.get("isError"):
                print(f"❌ OCI API error: {result.get('content', [{}])[0].get('text', 'Unknown error')}")
            else:
                print(f"✅ Test 1 successful!")
                content = result.get("content", [{}])[0].get("text", "{}")
                try:
                    data = json.loads(content)
                    items = data.get("items", [])
                    print(f"📊 Found {len(items)} instances")
                    print(f"🔍 Query used: {data.get('query', 'Unknown')}")
                    if data.get("fallback_reason"):
                        print(f"⚠️  Used fallback method: {data.get('method', 'Unknown')}")
                        print(f"📝 Fallback reason: {data.get('fallback_reason', 'Unknown')}")
                except Exception as e:
                    print(f"⚠️  Could not parse response: {e}")
        
        # Test 2: Simple search with single lifecycle state
        print("\n🔍 Test 2: Simple search with single lifecycle state...")
        tool_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "oci_compute_search_instances",
                "arguments": {
                    "lifecycle_state": "RUNNING",
                    "compartment_id": "ocid1.tenancy.oc1..aaaaaaaagy3yddkkampnhj3cqm5ar7w2p7tuq5twbojyycvol6wugfav3ckq",
                    "include_subtree": True
                }
            }
        }
        
        process.stdin.write(json.dumps(tool_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        tool_response = json.loads(response_line.strip())
        
        if "error" in tool_response:
            print(f"❌ Test 2 failed: {tool_response['error']}")
        else:
            result = tool_response.get("result", {})
            if result.get("isError"):
                print(f"❌ OCI API error: {result.get('content', [{}])[0].get('text', 'Unknown error')}")
            else:
                print(f"✅ Test 2 successful!")
                content = result.get("content", [{}])[0].get("text", "{}")
                try:
                    data = json.loads(content)
                    items = data.get("items", [])
                    print(f"📊 Found {len(items)} instances")
                    print(f"🔍 Query used: {data.get('query', 'Unknown')}")
                except Exception as e:
                    print(f"⚠️  Could not parse response: {e}")
        
        # Test 3: Regular list instances (fallback method)
        print("\n🔍 Test 3: Regular list instances (fallback method)...")
        tool_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "oci_compute_list_instances",
                "arguments": {
                    "compartment_id": "ocid1.tenancy.oc1..aaaaaaaagy3yddkkampnhj3cqm5ar7w2p7tuq5twbojyycvol6wugfav3ckq",
                    "lifecycle_state": "RUNNING",
                    "include_subtree": True
                }
            }
        }
        
        process.stdin.write(json.dumps(tool_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        tool_response = json.loads(response_line.strip())
        
        if "error" in tool_response:
            print(f"❌ Test 3 failed: {tool_response['error']}")
        else:
            result = tool_response.get("result", {})
            if result.get("isError"):
                print(f"❌ OCI API error: {result.get('content', [{}])[0].get('text', 'Unknown error')}")
            else:
                print(f"✅ Test 3 successful!")
                content = result.get("content", [{}])[0].get("text", "{}")
                try:
                    data = json.loads(content)
                    items = data.get("items", [])
                    print(f"📊 Found {len(items)} instances")
                except Exception as e:
                    print(f"⚠️  Could not parse response: {e}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        process.terminate()
        process.wait()

if __name__ == "__main__":
    asyncio.run(test_enhanced_search())
