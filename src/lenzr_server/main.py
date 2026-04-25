import logging
import os
from contextlib import asynccontextmanager

import fastapi
from fastapi.responses import JSONResponse

import lenzr_server
from lenzr_server.exceptions import NotFoundException
from lenzr_server.routes import tag_router, upload_router
from lenzr_server.thumbnail_service import InMemoryThumbnailCache
from lenzr_server.webhook import WebhookPayload, webhook_notifier_from_env

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    app.state.thumbnail_cache = InMemoryThumbnailCache()
    with webhook_notifier_from_env() as notifier:
        app.state.webhook_notifier = notifier
        yield


app = fastapi.FastAPI(
    title="Lenzr Server",
    version=lenzr_server.__version__,
    lifespan=lifespan,
)

app.include_router(upload_router)
app.include_router(tag_router)


@app.webhooks.post("upload.created")
def upload_created(body: WebhookPayload):
    """Sent as an HTTP POST to the configured `WEBHOOK_URL` when a new upload is created.

    If `WEBHOOK_SECRET` is set, the request body is signed with HMAC-SHA256 and the
    signature is supplied in the `X-Lenzr-Signature` header as `sha256=<hex_digest>`.
    """


@app.exception_handler(NotFoundException)
async def not_found_handler(request: fastapi.Request, exc: NotFoundException):
    return JSONResponse(status_code=404, content={"detail": exc.detail})
