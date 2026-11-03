from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/add")
def add(a: int, b: int) -> dict[str, int]:
    return {"result": a + b}
