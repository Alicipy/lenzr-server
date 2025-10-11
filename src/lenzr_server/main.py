
import fastapi
from fastapi import Depends, File, HTTPException, UploadFile

from lenzr_server.schemas import (
    ErrorResponse,
    ImageResponse,
    UploadResponse,
    UploadsListResponse,
)
from lenzr_server.upload_id_creators.hashing_id_creator import HashingIDCreator
from lenzr_server.upload_id_creators.id_creator import IDCreator

app = fastapi.FastAPI(
    title="Lenzr Server",
)

STORE: dict[str, tuple[bytes, str]] = {}

def get_id_creator():
    creator = HashingIDCreator(seed=32)
    return creator

@app.put(
    "/uploads",
    summary="Upload a file",
    description="Upload a file to the server and receive an upload ID",
    response_model=UploadResponse,
    status_code=201,
    responses={
        201: {
            "description": "File uploaded successfully",
        },
        400: {
            "description": "Bad request - invalid file",
            "model": ErrorResponse
        }
    },
)
async def upload_file(
    upload: UploadFile = File(
        ...,
        description="Image file to upload",
        media_type="image/*"
    ),
    id_creator: IDCreator = Depends(get_id_creator),
):
    content = await upload.read()
    content_type = upload.content_type
    if content_type is None or not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Bad request - invalid file")

    upload_id = id_creator.create_upload_id(content)
    STORE[upload_id] = (content, content_type)

    return UploadResponse(upload_id=upload_id)

@app.get(
    "/uploads/{upload_id}",
    summary="Get image",
    description="Download an uploaded image by ID",
    response_class=ImageResponse,
    status_code=200,
    responses = {
        200: {
            "description": "Image content",
        },
        404: {
            "description": "Upload not found",
            "model": ErrorResponse
        }}
)
async def get_upload(upload_id: str):
    if upload_id not in STORE:
        raise HTTPException(status_code=404, detail="Upload not found")

    content, content_type = STORE[upload_id]
    return ImageResponse(content=content, media_type=content_type)

@app.get(
    "/uploads",
    summary="List all uploads",
    description="Get a list of all upload IDs currently stored on the server",
    response_model=UploadsListResponse,
    status_code=200,
    responses={
        200: {
            "description": "List of upload IDs",
        }
    },
)
@app.get("/uploads")
async def list_uploads():
    return UploadsListResponse(uploads=list(STORE.keys()))