"""MCP クライアント CLI。

mcp-client tools
mcp-client call add --args '{"a": 1, "b": 2}'
"""

import argparse
import asyncio
import json
import os
import sys
from typing import Any

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import OAuthClientInformationFull
from pydantic import AnyUrl

from mcp_client.auth import REDIRECT_URI, InMemoryTokenStorage, create_provider

MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8001/mcp")
# 指定すると DCR をせず、事前登録済みの公開クライアント (demo realm の mcp-client) を使う
CLIENT_ID = os.environ.get("MCP_CLIENT_ID")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mcp-client", description=__doc__)
    parser.add_argument("--url", default=MCP_SERVER_URL, help="MCP サーバーの URL")
    parser.add_argument(
        "--client-id",
        default=CLIENT_ID,
        help="事前登録済みクライアント ID (未指定なら Dynamic Client Registration)",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("tools", help="ツール一覧を表示")
    call = sub.add_parser("call", help="ツールを呼び出す")
    call.add_argument("name", help="ツール名")
    call.add_argument("--args", default="{}", help='引数の JSON (例: {"a": 1})')
    return parser


def make_storage(client_id: str | None) -> InMemoryTokenStorage:
    if not client_id:
        return InMemoryTokenStorage()
    return InMemoryTokenStorage(
        OAuthClientInformationFull(
            client_id=client_id,
            redirect_uris=[AnyUrl(REDIRECT_URI)],
            token_endpoint_auth_method="none",
        )
    )


async def run_command(
    url: str, client_id: str | None, command: str, name: str = "", args: str = "{}"
) -> Any:
    provider = create_provider(url, make_storage(client_id))
    async with httpx2.AsyncClient(auth=provider, timeout=30) as http_client:
        transport = streamable_http_client(url, http_client=http_client)
        async with Client(transport) as client:
            if command == "tools":
                result = await client.list_tools()
                return [
                    {"name": t.name, "description": t.description} for t in result.tools
                ]
            call_result = await client.call_tool(name, json.loads(args))
            if call_result.is_error:
                raise RuntimeError(f"ツールがエラーを返しました: {call_result.content}")
            if call_result.structured_content is not None:
                return call_result.structured_content
            return [c.model_dump() for c in call_result.content]


def run() -> None:
    ns = build_parser().parse_args()
    try:
        output = asyncio.run(
            run_command(
                ns.url,
                ns.client_id,
                ns.command,
                getattr(ns, "name", ""),
                getattr(ns, "args", "{}"),
            )
        )
    except (RuntimeError, ValueError) as e:
        sys.exit(f"error: {e}")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
