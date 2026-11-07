import asyncio

import pytest

from mcp_client import auth
from mcp_client.main import build_parser, make_storage


def test_parse_callback_returns_code_and_state() -> None:
    result = auth.parse_callback("GET /callback?code=abc&state=xyz HTTP/1.1")
    assert (result.code, result.state) == ("abc", "xyz")


def test_parse_callback_raises_on_error() -> None:
    with pytest.raises(RuntimeError, match="access_denied"):
        auth.parse_callback("GET /callback?error=access_denied HTTP/1.1")


def test_parse_callback_raises_without_code() -> None:
    with pytest.raises(RuntimeError):
        auth.parse_callback("GET /callback HTTP/1.1")


async def test_wait_for_callback_receives_code() -> None:
    task = asyncio.create_task(auth.wait_for_callback("127.0.0.1", 0 + 38765, 5))
    await asyncio.sleep(0.2)
    _, writer = await asyncio.open_connection("127.0.0.1", 38765)
    writer.write(b"GET /callback?code=abc&state=s HTTP/1.1\r\n\r\n")
    await writer.drain()
    result = await task
    writer.close()
    assert (result.code, result.state) == ("abc", "s")


async def test_storage_uses_preregistered_client() -> None:
    storage = make_storage("mcp-client")
    info = await storage.get_client_info()
    assert info is not None
    assert info.client_id == "mcp-client"
    assert await make_storage(None).get_client_info() is None


def test_parser_call_command() -> None:
    ns = build_parser().parse_args(["call", "add", "--args", '{"a": 1}'])
    assert (ns.command, ns.name, ns.args) == ("call", "add", '{"a": 1}')


def test_strip_registration_scope() -> None:
    import httpx2

    req = httpx2.Request(
        "POST",
        "http://kc/realms/demo/clients-registrations/openid-connect",
        json={"client_name": "x", "scope": "openid address"},
    )
    assert "scope" not in auth.strip_registration_scope(req).read().decode()
    other = httpx2.Request("POST", "http://kc/token", json={"scope": "a"})
    assert auth.strip_registration_scope(other) is other
