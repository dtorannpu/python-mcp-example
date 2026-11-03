from unittest.mock import MagicMock

import httpx2
import pytest
from mcp import Client
from pytest_mock import MockerFixture

from mcp_server import main


@pytest.fixture
def api_client(mocker: MockerFixture) -> MagicMock:
    """httpx2.AsyncClient を差し替え、`async with` で得られるクライアントのモックを返す。"""
    client_cls = mocker.patch.object(main.httpx2, "AsyncClient")
    client = client_cls.return_value.__aenter__.return_value
    client.cls = client_cls
    client.get = mocker.AsyncMock(
        return_value=mocker.Mock(json=mocker.Mock(return_value={"result": 3}))
    )
    return client


async def test_add_calls_api(mocker: MockerFixture, api_client: MagicMock) -> None:
    assert await main.add(1, 2) == 3
    api_client.cls.assert_called_once_with(base_url=main.API_URL, headers={})
    api_client.get.assert_awaited_once_with("/add", params={"a": 1, "b": 2})


async def test_add_raises_on_api_error(
    mocker: MockerFixture, api_client: MagicMock
) -> None:
    api_client.get.return_value.raise_for_status.side_effect = httpx2.HTTPStatusError(
        "500", request=mocker.Mock(), response=mocker.Mock(status_code=500)
    )
    with pytest.raises(httpx2.HTTPStatusError):
        await main.add(1, 2)


async def test_add_tool_via_mcp(
    mocker: MockerFixture, api_client: MagicMock
) -> None:
    api_client.get.return_value.json.return_value = {"result": 9}
    async with Client(main.mcp) as client:
        result = await client.call_tool("add", {"a": 4, "b": 5})
    assert result.structured_content == {"result": 9}
    api_client.get.assert_awaited_once_with("/add", params={"a": 4, "b": 5})


async def test_add_exchanges_token_for_api(
    mocker: MockerFixture, api_client: MagicMock
) -> None:
    mocker.patch.object(
        main, "get_access_token", return_value=mocker.Mock(token="user-token")
    )
    exchange = mocker.patch.object(
        main, "exchange_token", new=mocker.AsyncMock(return_value="api-token")
    )
    assert await main.add(1, 2) == 3
    exchange.assert_awaited_once_with("user-token")
    api_client.cls.assert_called_once_with(
        base_url=main.API_URL, headers={"Authorization": "Bearer api-token"}
    )
