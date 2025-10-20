import fastapi

from lenzr_server.db import db_lifetime
from lenzr_server.routes import upload_router

app = fastapi.FastAPI(
    title="Lenzr Server",
    lifespan=db_lifetime,
)

app.include_router(upload_router)
