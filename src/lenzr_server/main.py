import fastapi

app = fastapi.FastAPI(
    title="Lenzr Server",
)

@app.get("/")
async def hello_world():
    return {"message": "Hello, world!"}
