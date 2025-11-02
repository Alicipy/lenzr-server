import fastapi

from lenzr_server.routes import upload_router

app = fastapi.FastAPI(
    title="Lenzr Server",
)

app.include_router(upload_router)
