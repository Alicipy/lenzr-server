import logging
import os
from contextlib import asynccontextmanager
from typing import Annotated

import fastapi
from fastapi import Header
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


@app.get("/health", tags=["Health"], summary="Liveness probe")
async def health() -> dict[str, str]:
    """Unauthenticated probe for orchestrators (Docker, Kubernetes, etc.)."""
    return {"status": "ok"}


@app.webhooks.post(
    "upload.created",
    status_code=204,
    response_class=fastapi.Response,
    responses={
        204: {"description": "Acknowledged."},
        "default": {"description": "Receiver indicated an error."},
    },
)
def upload_created(
    body: WebhookPayload,
    x_lenzr_timestamp: Annotated[
        str | None,
        Header(
            description=(
                "Dispatch time as Unix seconds. Sent only when `WEBHOOK_SECRET` is "
                "configured. Receivers should reject requests whose timestamp is "
                "older than a few minutes to defend against replays."
            ),
        ),
    ] = None,
    x_lenzr_signature: Annotated[
        str | None,
        Header(
            description=(
                "HMAC-SHA256 signature over the bytes `<timestamp>.<raw_body>`, "
                "encoded as `sha256=<hex_digest>`. Sent only when `WEBHOOK_SECRET` "
                "is configured. Verify with `hmac.compare_digest`."
            ),
        ),
    ] = None,
):
    """Sent as an HTTP POST to the configured `WEBHOOK_URL` when a new upload is created.

    If `WEBHOOK_SECRET` is set, the request is signed with HMAC-SHA256 and the
    `X-Lenzr-Timestamp` and `X-Lenzr-Signature` headers are included.

    Delivery is fire-and-forget: a non-2xx response or transport error is
    logged and the dispatch is dropped — there is no retry.
    """


@app.exception_handler(NotFoundException)
async def not_found_handler(request: fastapi.Request, exc: NotFoundException):
    return JSONResponse(status_code=404, content={"detail": exc.detail})
