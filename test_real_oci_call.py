#!/usr/bin/env python3
"""
Test script to make a real OCI API call through MCP
"""
import asyncio
import json
import subprocess
import sys

async def test_real_oci_call():
    """Test a real OCI API call through MCP"""
    print("🔍 Testing real OCI API call through MCP...")
    
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
        
        # Test get_server_info tool first
        tool_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "get_server_info",
                "arguments": {}
            }
        }
        
        process.stdin.write(json.dumps(tool_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        tool_response = json.loads(response_line.strip())
        print(f"✅ Server info: {tool_response.get('result', {})}")
        
        # Test compute list instances with tenancy OCID
        print("\n🔍 Testing OCI Compute API call...")
        tool_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "oci_compute_list_instances",
                "arguments": {
                    "compartment_id": "ocid1.tenancy.oc1..aaaaaaaagy3yddkkampnhj3cqm5ar7w2p7tuq5twbojyycvol6wugfav3ckq"
                }
            }
        }
        
        process.stdin.write(json.dumps(tool_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        tool_response = json.loads(response_line.strip())
        
        if "error" in tool_response:
            print(f"❌ API call failed: {tool_response['error']}")
        else:
            result = tool_response.get("result", {})
            if result.get("isError"):
                print(f"❌ OCI API error: {result.get('content', [{}])[0].get('text', 'Unknown error')}")
            else:
                print(f"✅ OCI API call successful!")
                # Try to parse the response
                try:
                    content = result.get("content", [{}])[0].get("text", "{}")
                    data = json.loads(content)
                    items = data.get("items", [])
                    print(f"📊 Found {len(items)} compute instances")
                    if items:
                        print("📋 Sample instances:")
                        for i, item in enumerate(items[:3]):  # Show first 3
                            print(f"  {i+1}. {item.get('displayName', 'Unknown')} ({item.get('lifecycleState', 'Unknown state')})")
                except Exception as e:
                    print(f"⚠️  Could not parse response: {e}")
                    print(f"Raw response: {content[:200]}...")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        process.terminate()
        process.wait()

if __name__ == "__main__":
    asyncio.run(test_real_oci_call())
