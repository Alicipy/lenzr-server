from contextlib import asynccontextmanager

import fastapi
from fastapi.responses import JSONResponse

import lenzr_server
from lenzr_server.exceptions import NotFoundException
from lenzr_server.routes import tag_router, upload_router
from lenzr_server.thumbnail_service import InMemoryThumbnailCache


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    app.state.thumbnail_cache = InMemoryThumbnailCache()
    yield


app = fastapi.FastAPI(
    title="Lenzr Server",
    version=lenzr_server.__version__,
    lifespan=lifespan,
)

app.include_router(upload_router)
app.include_router(tag_router)


@app.exception_handler(NotFoundException)
async def not_found_handler(request: fastapi.Request, exc: NotFoundException):
    return JSONResponse(status_code=404, content={"detail": exc.detail})
