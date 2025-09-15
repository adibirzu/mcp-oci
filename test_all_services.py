#!/usr/bin/env python3
"""
Test script to verify all MCP OCI services are working properly
"""
import asyncio
import json
import subprocess
import sys
import time
from typing import Dict, Any, List

# List of all available services
SERVICES = [
    "compute", "iam", "usageapi", "monitoring", "networking", "objectstorage",
    "database", "blockstorage", "oke", "functions", "vault", "loadbalancer",
    "dns", "kms", "events", "streaming"
]

async def test_mcp_service(service_name: str) -> Dict[str, Any]:
    """Test a single MCP service"""
    print(f"\n🧪 Testing {service_name} service...")
    
    # Start the MCP server
    process = subprocess.Popen(
        ["/Users/abirzu/.pyenv/versions/3.11.9/bin/python", "-m", "mcp_oci_fastmcp", 
         service_name, "--profile", "DEFAULT", "--region", "eu-frankfurt-1"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    result = {
        "service": service_name,
        "status": "unknown",
        "tools_count": 0,
        "error": None,
        "server_info": None
    }
    
    try:
        # Wait for server to start
        await asyncio.sleep(2)
        
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
        if not response_line:
            result["status"] = "failed"
            result["error"] = "No response to initialize"
            return result
            
        init_response = json.loads(response_line.strip())
        if "error" in init_response:
            result["status"] = "failed"
            result["error"] = f"Initialize error: {init_response['error']}"
            return result
        
        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        process.stdin.write(json.dumps(initialized_notification) + "\n")
        process.stdin.flush()
        
        # Send tools/list request
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        process.stdin.write(json.dumps(tools_request) + "\n")
        process.stdin.flush()
        
        # Read tools response
        response_line = process.stdout.readline()
        if not response_line:
            result["status"] = "failed"
            result["error"] = "No response to tools/list"
            return result
            
        tools_response = json.loads(response_line.strip())
        if "error" in tools_response:
            result["status"] = "failed"
            result["error"] = f"Tools list error: {tools_response['error']}"
            return result
        
        tools = tools_response.get("result", {}).get("tools", [])
        result["tools_count"] = len(tools)
        
        # Test get_server_info tool if available
        if any(tool["name"] == "get_server_info" for tool in tools):
            tool_request = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "get_server_info",
                    "arguments": {}
                }
            }
            
            process.stdin.write(json.dumps(tool_request) + "\n")
            process.stdin.flush()
            
            # Read tool response
            response_line = process.stdout.readline()
            if response_line:
                tool_response = json.loads(response_line.strip())
                if "result" in tool_response:
                    result["server_info"] = tool_response["result"]
        
        result["status"] = "success"
        print(f"✅ {service_name}: {len(tools)} tools available")
        
    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        print(f"❌ {service_name}: {str(e)}")
    
    finally:
        process.terminate()
        process.wait()
    
    return result

async def test_all_services():
    """Test all MCP services"""
    print("🚀 Testing all MCP OCI services...")
    
    results = []
    for service in SERVICES:
        result = await test_mcp_service(service)
        results.append(result)
        # Small delay between tests
        await asyncio.sleep(0.5)
    
    # Print summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]
    
    print(f"✅ Successful: {len(successful)}/{len(results)}")
    print(f"❌ Failed: {len(failed)}/{len(results)}")
    
    if successful:
        print("\n✅ WORKING SERVICES:")
        for result in successful:
            print(f"  - {result['service']}: {result['tools_count']} tools")
    
    if failed:
        print("\n❌ FAILED SERVICES:")
        for result in failed:
            print(f"  - {result['service']}: {result['error']}")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_all_services())
