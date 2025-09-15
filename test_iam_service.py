#!/usr/bin/env python3
"""
Test IAM service to get correct compartment information
"""
import asyncio
import json
import subprocess
import sys

async def test_iam_service():
    """Test IAM service to get compartment information"""
    print("🔍 Testing IAM service to get compartment information...")
    
    # Start the MCP server
    process = subprocess.Popen(
        ["/Users/abirzu/.pyenv/versions/3.11.9/bin/python", "-m", "mcp_oci_fastmcp", 
         "iam", "--profile", "DEFAULT", "--region", "eu-frankfurt-1"],
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
        print(f"✅ IAM Server initialized: {init_response.get('result', {}).get('serverInfo', {})}")
        
        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        process.stdin.write(json.dumps(initialized_notification) + "\n")
        process.stdin.flush()
        
        # Test list compartments
        print("\n🔍 Testing OCI IAM API call - List Compartments...")
        tool_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "oci_iam_list_compartments",
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
                print(f"✅ OCI IAM API call successful!")
                # Try to parse the response
                try:
                    content = result.get("content", [{}])[0].get("text", "{}")
                    data = json.loads(content)
                    items = data.get("items", [])
                    print(f"📊 Found {len(items)} compartments")
                    if items:
                        print("📋 Available compartments:")
                        for i, item in enumerate(items[:5]):  # Show first 5
                            print(f"  {i+1}. {item.get('name', 'Unknown')} ({item.get('id', 'No ID')})")
                            print(f"      Lifecycle State: {item.get('lifecycleState', 'Unknown')}")
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
    asyncio.run(test_iam_service())
