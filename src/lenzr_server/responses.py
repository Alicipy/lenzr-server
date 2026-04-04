from fastapi.responses import Response

from lenzr_server.schemas import ErrorResponse

NOT_FOUND_RESPONSES = {404: {"description": "Not found", "model": ErrorResponse}}


class ImageResponse(Response):
    def __init__(self, content: bytes, media_type: str):
        super().__init__(
            content=content,
            media_type=media_type,
            headers={
                "Content-Length": str(len(content)),
                "Cache-Control": "public, max-age=3600",  # Cache images for 1 hour
            },
        )
