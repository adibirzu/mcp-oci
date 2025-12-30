import asyncio
from mcp_server_oci.server import mcp

async def main():
    print("Registered Tools:")
    tools = await mcp.get_tools()
    print(f"DEBUG: tools type: {type(tools)}")
    print(f"DEBUG: tools content: {tools}")
    
    # Adapt logic based on tools structure
    if isinstance(tools, dict):
         tool_names = list(tools.keys())
    elif isinstance(tools, list):
         # Check if items are strings or objects
         if tools and isinstance(tools[0], str):
             tool_names = tools
         else:
             tool_names = [t.name for t in tools]
    else:
        print("Unknown tools structure")
        exit(1)
        
    for name in tool_names:
        print(f"- {name}")

    expected = [
        "list_instances", 
        "start_instance", 
        "stop_instance", 
        "restart_instance",
        "get_instance_metrics",
        "get_logs",
        "troubleshoot_instance",
        "search_tools"
    ]

    missing = [t for t in expected if t not in tool_names]

    if missing:
        print(f"\n❌ FAILED: Missing tools: {missing}")
        exit(1)
    else:
        print("\n✅ SUCCESS: All expected tools registered.")

if __name__ == "__main__":
    asyncio.run(main())