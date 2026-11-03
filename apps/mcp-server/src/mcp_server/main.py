import os

import httpx2
from mcp.server import MCPServer
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.httpx import HTTPX2ClientInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

API_URL = os.environ.get("API_URL", "http://api:8000")

# OTEL_EXPORTER_OTLP_ENDPOINT / OTEL_SERVICE_NAME は環境変数から読み込まれる
provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)
HTTPX2ClientInstrumentor().instrument()

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
