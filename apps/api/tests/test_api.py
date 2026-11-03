from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_read_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}


def test_add() -> None:
    response = client.get("/add", params={"a": 1, "b": 2})
    assert response.status_code == 200
    assert response.json() == {"result": 3}


def test_add_invalid_param() -> None:
    response = client.get("/add", params={"a": "x", "b": 2})
    assert response.status_code == 422
