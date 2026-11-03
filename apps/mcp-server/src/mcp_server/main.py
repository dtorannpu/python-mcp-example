import os

import httpx2
from mcp.server import MCPServer
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.httpx import HTTPX2ClientInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from mcp_server.auth import (
    ISSUER,
    RESOURCE_URL,
    KeycloakTokenVerifier,
    exchange_token,
)

API_URL = os.environ.get("API_URL", "http://api:8000")

# OTEL_EXPORTER_OTLP_ENDPOINT / OTEL_SERVICE_NAME は環境変数から読み込まれる
provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)
HTTPX2ClientInstrumentor().instrument()
tracer = trace.get_tracer(__name__)

mcp = MCPServer(
    "Demo",
    token_verifier=KeycloakTokenVerifier(),
    auth=AuthSettings(
        issuer_url=ISSUER,
        resource_server_url=RESOURCE_URL,
        # aud の検証は KeycloakTokenVerifier 側で行う
        validate_token_resource=False,
    ),
)


@mcp.tool()
async def add(a: int, b: int) -> int:
    """Add two numbers (API サーバーの /add を呼び出す)。"""
    # 受け取ったトークンを API 向けのトークンに交換して呼び出す
    access_token = get_access_token()
    with tracer.start_as_current_span("tool.add") as span:
        headers = {}
        if access_token:
            # トークンの sub (ユーザーID) をトレースに記録する
            if access_token.subject:
                span.set_attribute("enduser.id", access_token.subject)
            api_token = await exchange_token(access_token.token)
            headers["Authorization"] = f"Bearer {api_token}"
        async with httpx2.AsyncClient(base_url=API_URL, headers=headers) as client:
            response = await client.get("/add", params={"a": a, "b": b})
            response.raise_for_status()
            return response.json()["result"]


if __name__ == "__main__":
    mcp.run("streamable-http", host="0.0.0.0", port=8001)
