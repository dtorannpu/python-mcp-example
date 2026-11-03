from fastapi import Depends, FastAPI

from api.auth import verify_token

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/add", dependencies=[Depends(verify_token)])
def add(a: int, b: int) -> dict[str, int]:
    return {"result": a + b}
