from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from lenzr_server.dependencies import check_login_valid, get_tag_service, get_upload_service
from lenzr_server.responses import NOT_FOUND_RESPONSES, ImageResponse
from lenzr_server.schemas import (
    ErrorResponse,
    TagListResponse,
    TagsUpdateRequest,
    UploadMetaDataCreateResponse,
    UploadMetaDataDeleteResponse,
    UploadMetaDataPublicResponse,
    UploadWithTagsResponse,
)
from lenzr_server.tag_service import TagService
from lenzr_server.types import TagName, UploadID
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
    tags: list[TagName] = Query(default=[]),
    upload_service: UploadService = Depends(get_upload_service),
    tag_service: TagService = Depends(get_tag_service),
    _login_valid: None = Depends(check_login_valid),
):
    content = await upload.read()
    content_type = upload.content_type
    if content_type is None or not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Bad request - invalid file")

    try:
        upload_metadata = upload_service.add_upload(content, content_type)
        created = True
    except UploadAlreadyExistingException as aee:
        upload_metadata = UploadMetaDataPublicResponse(upload_id=aee.upload_id)
        created = False

    result_tags: list[TagName] = []
    if tags and created:
        result_tags = tag_service.set_tags(upload_metadata.upload_id, tags)

    response.status_code = 201 if created else 200
    return UploadMetaDataCreateResponse(upload_id=upload_metadata.upload_id, tags=result_tags)


@upload_router.get(
    "/search",
    summary="Search uploads by tags",
    description="Find uploads that have all specified tags (AND logic)",
    response_model=list[UploadWithTagsResponse],
    status_code=200,
    responses={
        200: {"description": "List of matching uploads with their tags"},
    },
)
async def search_uploads_by_tags(
    tags: list[TagName] = Query(..., description="Tags to search for (AND logic)"),
    offset: int = Query(0, description="Number of items to skip"),
    limit: int = Query(10, description="Maximum number of items to return"),
    tag_service: TagService = Depends(get_tag_service),
    _login_valid: None = Depends(check_login_valid),
):
    results = tag_service.search_by_tags(tags, offset=offset, limit=limit)
    return [UploadWithTagsResponse.from_upload_with_tags(r) for r in results]


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
    _login_valid: None = Depends(check_login_valid),
):
    return upload_service.delete_upload(upload_id)


@upload_router.put(
    "/{upload_id}/tags",
    summary="Set tags for an upload",
    description="Replace all tags for an upload with the provided list",
    response_model=UploadWithTagsResponse,
    status_code=200,
    responses={
        200: {"description": "Tags updated"},
        **NOT_FOUND_RESPONSES,
    },
)
async def set_upload_tags(
    upload_id: UploadID,
    body: TagsUpdateRequest,
    tag_service: TagService = Depends(get_tag_service),
    _login_valid: None = Depends(check_login_valid),
):
    tag_service.set_tags(upload_id, body.tags)
    result = tag_service.get_upload_with_tags(upload_id)
    return UploadWithTagsResponse.from_upload_with_tags(result)


@upload_router.get(
    "/{upload_id}/tags",
    summary="Get tags for an upload",
    description="Get all tags associated with an upload",
    response_model=UploadWithTagsResponse,
    status_code=200,
    responses={
        200: {"description": "Tags for the upload"},
        **NOT_FOUND_RESPONSES,
    },
)
async def get_upload_tags(
    upload_id: UploadID,
    tag_service: TagService = Depends(get_tag_service),
    _login_valid: None = Depends(check_login_valid),
):
    result = tag_service.get_upload_with_tags(upload_id)
    return UploadWithTagsResponse.from_upload_with_tags(result)


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


tag_router = APIRouter(prefix="/tags", tags=["Tags"])


@tag_router.get(
    "",
    summary="List all tags",
    description="Get a list of all tag names",
    response_model=TagListResponse,
    status_code=200,
    responses={
        200: {"description": "List of all tags"},
    },
)
async def list_all_tags(
    offset: int = Query(0, description="Number of items to skip"),
    limit: int = Query(100, description="Maximum number of items to return"),
    tag_service: TagService = Depends(get_tag_service),
    _login_valid: None = Depends(check_login_valid),
):
    tags = tag_service.list_all_tags(offset=offset, limit=limit)
    return TagListResponse(tags=tags)
