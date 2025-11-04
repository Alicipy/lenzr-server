from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from lenzr_server.dependencies import check_login_valid, get_upload_service
from lenzr_server.schemas import ErrorResponse, ImageResponse, UploadResponse, UploadsListResponse
from lenzr_server.types import UploadID
from lenzr_server.upload_service import AlreadyExistingException, NotFoundException, UploadService

upload_router = APIRouter()


@upload_router.post(
    "/uploads",
    summary="Upload a file",
    description="Upload a file to the server and receive an upload ID",
    response_model=UploadResponse,
    status_code=201,
    responses={
        201: {
            "description": "File uploaded successfully",
        },
        400: {"description": "Bad request - invalid file", "model": ErrorResponse},
        409: {"description": "Upload already exists", "model": ErrorResponse},
    },
)
async def upload_file(
    upload: UploadFile = File(..., description="Image file to upload", media_type="image/*"),
    upload_service: UploadService = Depends(get_upload_service),
    _login_valid: None = Depends(check_login_valid),
):
    content = await upload.read()
    content_type = upload.content_type
    if content_type is None or not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Bad request - invalid file")

    try:
        upload_id = upload_service.add_upload(content, content_type)
    except AlreadyExistingException:
        raise HTTPException(status_code=409, detail="Already exists")

    return UploadResponse(upload_id=upload_id)


@upload_router.get(
    "/uploads/{upload_id}",
    summary="Get image",
    description="Download an uploaded image by ID",
    response_class=ImageResponse,
    status_code=200,
    responses={
        200: {
            "description": "Image content",
        },
        404: {"description": "Upload not found", "model": ErrorResponse},
    },
)
async def get_upload(
    upload_id: UploadID,
    upload_service: UploadService = Depends(get_upload_service),
):
    try:
        content, content_type = upload_service.get_upload(upload_id)
    except NotFoundException:
        raise HTTPException(status_code=404, detail="Upload not found")

    return ImageResponse(content=content, media_type=content_type)


@upload_router.get(
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
async def list_uploads(
    upload_service: UploadService = Depends(get_upload_service),
    _login_valid: None = Depends(check_login_valid),
):
    ids = upload_service.list_uploads()

    return UploadsListResponse(uploads=list(ids))
