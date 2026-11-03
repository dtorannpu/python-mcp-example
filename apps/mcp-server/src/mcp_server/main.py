import os

import httpx2
from mcp.server import MCPServer

API_URL = os.environ.get("API_URL", "http://api:8000")

mcp = MCPServer("Demo")


@mcp.tool()
async def add(a: int, b: int) -> int:
    """Add two numbers (API サーバーの /add を呼び出す)。"""
    async with httpx2.AsyncClient(base_url=API_URL) as client:
        response = await client.get("/add", params={"a": a, "b": b})
        response.raise_for_status()
        return response.json()["result"]


if __name__ == "__main__":
    mcp.run("streamable-http", host="0.0.0.0", port=8001)
