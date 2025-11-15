import fastapi

import lenzr_server
from lenzr_server.routes import upload_router

app = fastapi.FastAPI(
    title="Lenzr Server",
    version=lenzr_server.__version__,
)

app.include_router(upload_router)
