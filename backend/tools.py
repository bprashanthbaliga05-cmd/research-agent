# Web search, doc reader
import os
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def search_with_mcp(query: str) -> str:
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "tavily-mcp@0.1.4"],
        env={
            **os.environ,
            "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY")
        }
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # See what tools the MCP server exposes
            tools = await session.list_tools()
            print("MCP tools available:", [t.name for t in tools.tools])

            # Call the search tool
            result = await session.call_tool(
                "tavily-search",
                arguments={
                    "query": query,
                    "max_results": 5
                }
            )

            # Extract text from result
            if result.content:
                # MCP returns a list of content blocks
                full_text = "\n".join(
                    block.text for block in result.content
                    if hasattr(block, "text")
                )
                return full_text

            return "No results found"