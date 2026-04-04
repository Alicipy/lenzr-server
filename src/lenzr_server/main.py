import fastapi
from fastapi.responses import JSONResponse

import lenzr_server
from lenzr_server.exceptions import NotFoundException
from lenzr_server.routes import upload_router

app = fastapi.FastAPI(
    title="Lenzr Server",
    version=lenzr_server.__version__,
)

app.include_router(upload_router)


@app.exception_handler(NotFoundException)
async def not_found_handler(request: fastapi.Request, exc: NotFoundException):
    return JSONResponse(status_code=404, content={"detail": exc.detail})
