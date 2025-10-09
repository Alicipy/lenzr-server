from fastapi.responses import Response
from pydantic import BaseModel


class UploadResponse(BaseModel):
    upload_id: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "upload_id": "1"
            },
        },
    }

class UploadsListResponse(BaseModel):
    uploads: list[str]

    model_config = {
        "json_schema_extra": {
            "example": {
                "uploads": ["0", "2", "3"]
            },
        },
    }

class ErrorResponse(BaseModel):
    detail: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "detail": "Upload not found"
            },
        },
    }

class ImageResponse(Response):

    def __init__(self, content: bytes, media_type: str):
        super().__init__(
            content=content,
            media_type=media_type,
            headers={
                "Content-Length": str(len(content)),
                "Cache-Control": "public, max-age=3600"  # Cache images for 1 hour
            }
        )