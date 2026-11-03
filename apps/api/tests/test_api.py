from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from api.auth import verify_token
from api.main import app

client = TestClient(app)


@pytest.fixture
def authenticated() -> Iterator[None]:
    app.dependency_overrides[verify_token] = lambda: {"sub": "test"}
    yield
    app.dependency_overrides.clear()


def test_read_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}


@pytest.mark.usefixtures("authenticated")
def test_add() -> None:
    response = client.get("/add", params={"a": 1, "b": 2})
    assert response.status_code == 200
    assert response.json() == {"result": 3}


@pytest.mark.usefixtures("authenticated")
def test_add_invalid_param() -> None:
    response = client.get("/add", params={"a": "x", "b": 2})
    assert response.status_code == 422


def test_add_requires_token() -> None:
    response = client.get("/add", params={"a": 1, "b": 2})
    assert response.status_code == 401


def test_add_rejects_invalid_token() -> None:
    response = client.get(
        "/add",
        params={"a": 1, "b": 2},
        headers={"Authorization": "Bearer invalid"},
    )
    assert response.status_code == 401
