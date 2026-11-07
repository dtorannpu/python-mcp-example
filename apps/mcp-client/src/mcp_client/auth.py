"""OAuth (Authorization Code + PKCE) のためのヘルパー。

トークン・クライアント情報はメモリ上にだけ保持します (実行ごとにログインが必要)。
"""

import asyncio
import json
import webbrowser
from collections.abc import AsyncGenerator
from urllib.parse import parse_qs, urlparse

import httpx2
from mcp.client.auth import OAuthClientProvider
from mcp.shared.auth import (
    AuthorizationCodeResult,
    OAuthClientInformationFull,
    OAuthClientMetadata,
    OAuthToken,
)
from pydantic import AnyUrl

CALLBACK_HOST = "127.0.0.1"
CALLBACK_PORT = 3030
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/callback"

_RESPONSE = (
    "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n"
    "Connection: close\r\n\r\n"
    "<html><body><h1>認証が完了しました</h1><p>このタブは閉じて構いません。</p></body></html>"
)


class InMemoryTokenStorage:
    """TokenStorage 実装。`client_info` を渡すと DCR をせず事前登録済みクライアントを使う。"""

    def __init__(self, client_info: OAuthClientInformationFull | None = None) -> None:
        self._tokens: OAuthToken | None = None
        self._client_info = client_info

    async def get_tokens(self) -> OAuthToken | None:
        return self._tokens

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self._tokens = tokens

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        return self._client_info

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self._client_info = client_info


async def open_browser(url: str) -> None:
    """認可 URL をブラウザで開く (開けない場合に備えて URL も表示する)。"""
    print(f"ブラウザでログインしてください:\n  {url}")
    webbrowser.open(url)


def parse_callback(request_line: str) -> AuthorizationCodeResult:
    """`GET /callback?code=...&state=... HTTP/1.1` から認可コードを取り出す。"""
    parts = request_line.split(" ")
    target = parts[1] if len(parts) > 1 else ""
    query = parse_qs(urlparse(target).query)
    if "error" in query:
        description = query.get("error_description", [""])[0]
        raise RuntimeError(f"認可エラー: {query['error'][0]} {description}".strip())
    if "code" not in query:
        raise RuntimeError(f"認可コードがありません: {request_line!r}")
    return AuthorizationCodeResult(
        code=query["code"][0],
        state=query.get("state", [None])[0],
        iss=query.get("iss", [None])[0],
    )


async def wait_for_callback(
    host: str = CALLBACK_HOST, port: int = CALLBACK_PORT, timeout: float = 300
) -> AuthorizationCodeResult:
    """リダイレクト先のローカル HTTP サーバーを立て、認可コードを受け取る。"""
    loop = asyncio.get_running_loop()
    result: asyncio.Future[AuthorizationCodeResult] = loop.create_future()

    async def handle(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            line = (await reader.readline()).decode("latin-1").strip()
            # /favicon.ico などのリクエストは無視する
            if " /callback" not in line:
                writer.write(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n")
                return
            try:
                parsed = parse_callback(line)
            except RuntimeError as e:
                if not result.done():
                    result.set_exception(e)
            else:
                if not result.done():
                    result.set_result(parsed)
            writer.write(_RESPONSE.encode())
        finally:
            await writer.drain()
            writer.close()

    server = await asyncio.start_server(handle, host, port)
    try:
        async with asyncio.timeout(timeout):
            return await result
    finally:
        server.close()
        await server.wait_closed()


class DcrOAuthClientProvider(OAuthClientProvider):
    """Keycloak の匿名 DCR に合わせてスコープを絞る OAuthClientProvider。

    SDK は PRM に scopes_supported が無いと認可サーバーの全スコープ (openid, address, ...) を
    要求するが、DCR クライアントに割り当てられていないスコープは Keycloak が拒否する
    (登録時: 403 insufficient_scope / 認可時: invalid_scope)。そのため
    - 登録リクエストからは scope を除く
    - 認可リクエストでは `auth_scope` だけを要求する (デフォルトスコープは指定不要で付与される)
    """

    auth_scope: str | None = "openid"

    async def _perform_authorization_code_grant(self) -> tuple[str, str]:
        self.context.client_metadata.scope = self.auth_scope
        return await super()._perform_authorization_code_grant()

    async def _auth_flow(
        self, request: httpx2.Request
    ) -> AsyncGenerator[httpx2.Request, httpx2.Response]:
        flow = super()._auth_flow(request)
        try:
            outgoing = await anext(flow)
            while True:
                response = yield strip_registration_scope(outgoing)
                outgoing = await flow.asend(response)
        except StopAsyncIteration:
            return


def strip_registration_scope(request: httpx2.Request) -> httpx2.Request:
    """JSON ボディを持つ登録 (POST) リクエストなら `scope` を取り除いて返す。"""
    if request.method != "POST" or "registration" not in request.url.path.lower():
        return request
    try:
        body = json.loads(request.content)
    except ValueError:
        return request
    if not isinstance(body, dict) or "scope" not in body:
        return request
    del body["scope"]
    return httpx2.Request(
        "POST", request.url, headers={"Content-Type": "application/json"}, json=body
    )


def create_provider(
    server_url: str,
    storage: InMemoryTokenStorage,
    scope: str | None = None,
) -> OAuthClientProvider:
    return DcrOAuthClientProvider(
        server_url=server_url,
        client_metadata=OAuthClientMetadata(
            client_name="python-mcp-example client",
            redirect_uris=[AnyUrl(REDIRECT_URI)],
            token_endpoint_auth_method="none",  # 公開クライアント (PKCE)
            grant_types=["authorization_code", "refresh_token"],
            scope=scope,
        ),
        storage=storage,
        redirect_handler=open_browser,
        callback_handler=wait_for_callback,
    )
