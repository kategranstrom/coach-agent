"""Smoke test: launch the Garmin MCP server over stdio and pull real recent activities.

Confirms the auth tokens saved by `uvx garmin-connect-mcp auth` work end-to-end
before anything else in the project is built on top of this connection.
"""
import asyncio
import shutil

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

UVX = shutil.which("uvx") or "uvx"
SERVER = StdioServerParameters(command=UVX, args=["garmin-connect-mcp"])


async def main():
    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print(f"Connected. {len(tools.tools)} tools available:")
            for tool in tools.tools:
                print(f"  - {tool.name}")

            print("\nFetching recent activities...")
            result = await session.call_tool("query_activities", arguments={"limit": 5})
            for block in result.content:
                if hasattr(block, "text"):
                    print(block.text)


if __name__ == "__main__":
    asyncio.run(main())
