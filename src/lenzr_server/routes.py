from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from lenzr_server.dependencies import check_login_valid, get_upload_service
from lenzr_server.models.uploads import (
    UploadMetaDataCreateResponse,
    UploadMetaDataDeleteResponse,
    UploadMetaDataPublicResponse,
)
from lenzr_server.responses import NOT_FOUND_RESPONSES
from lenzr_server.schemas import ErrorResponse, ImageResponse
from lenzr_server.types import UploadID
from lenzr_server.upload_service import UploadAlreadyExistingException, UploadService

upload_router = APIRouter(prefix="/uploads", tags=["Uploads"])


@upload_router.post(
    "",
    summary="Upload a file",
    description="Upload a file to the server and receive an upload ID",
    response_model=UploadMetaDataCreateResponse,
    status_code=201,
    responses={
        200: {
            "description": "Upload already exists",
        },
        201: {
            "description": "File uploaded successfully",
        },
        400: {"description": "Bad request - invalid file", "model": ErrorResponse},
    },
)
async def upload_file(
    response: Response,
    upload: UploadFile = File(..., description="Image file to upload", media_type="image/*"),
    upload_service: UploadService = Depends(get_upload_service),
    _login_valid: None = Depends(check_login_valid),
):
    content = await upload.read()
    content_type = upload.content_type
    if content_type is None or not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Bad request - invalid file")

    try:
        upload = upload_service.add_upload(content, content_type)
        created = True
    except UploadAlreadyExistingException as aee:
        upload = UploadMetaDataPublicResponse(upload_id=aee.upload_id)
        created = False

    response.status_code = 201 if created else 200
    return upload


@upload_router.get(
    "/{upload_id}",
    summary="Get image",
    description="Download an uploaded image by ID",
    response_class=ImageResponse,
    status_code=200,
    responses={
        200: {
            "description": "Image content",
        },
        **NOT_FOUND_RESPONSES,
    },
)
async def get_upload(
    upload_id: UploadID,
    upload_service: UploadService = Depends(get_upload_service),
):
    content, content_type = upload_service.get_upload(upload_id)
    return ImageResponse(content=content, media_type=content_type)


@upload_router.delete(
    "/{upload_id}",
    summary="Delete image",
    description="Delete an uploaded image by ID",
    status_code=200,
    responses={
        200: {
            "description": "Image deleted",
        },
        **NOT_FOUND_RESPONSES,
    },
    response_model=UploadMetaDataDeleteResponse,
)
async def delete_upload(
    upload_id: UploadID,
    upload_service: UploadService = Depends(get_upload_service),
):
    return upload_service.delete_upload(upload_id)


@upload_router.get(
    "",
    summary="List all uploads",
    description="Get a list of all upload IDs currently stored on the server in "
    "descending order of upload time.",
    response_model=list[UploadMetaDataPublicResponse],
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
    offset: int = Query(0, description="Number of items to skip"),
    limit: int = Query(10, description="Maximum number of items to return"),
):
    uploads = upload_service.list_uploads(offset=offset, limit=limit)

    return uploads
