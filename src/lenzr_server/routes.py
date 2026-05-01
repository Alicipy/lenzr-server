from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from lenzr_server.dependencies import (
    check_login_valid,
    get_tag_service,
    get_thumbnail_service,
    get_upload_service,
    get_webhook_notifier,
)
from lenzr_server.responses import NOT_FOUND_RESPONSES, ImageResponse
from lenzr_server.schemas import (
    ErrorResponse,
    TagListResponse,
    TagsUpdateRequest,
    UploadMetaDataCreateResponse,
    UploadMetaDataDeleteResponse,
    UploadWithTagsResponse,
)
from lenzr_server.tag_service import TagService
from lenzr_server.thumbnail_service import InvalidImageException, ThumbnailService
from lenzr_server.types import TagName, UploadID
from lenzr_server.upload_service import UploadAlreadyExistingException, UploadService
from lenzr_server.webhook import WebhookNotifier

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
    background_tasks: BackgroundTasks,
    upload: UploadFile = File(..., description="Image file to upload", media_type="image/*"),
    tags: list[TagName] = Query(default=[]),
    upload_service: UploadService = Depends(get_upload_service),
    tag_service: TagService = Depends(get_tag_service),
    webhook_notifier: WebhookNotifier = Depends(get_webhook_notifier),
    _login_valid: None = Depends(check_login_valid),
):
    content = await upload.read()
    content_type = upload.content_type
    if content_type is None or not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Bad request - invalid file")

    try:
        upload_id = upload_service.add_upload(content, content_type).upload_id
        created = True
    except UploadAlreadyExistingException as aee:
        upload_id = aee.upload_id
        created = False

    result_tags: list[TagName] = []
    if tags and created:
        result_tags = tag_service.set_tags(upload_id, tags)

    if created:
        background_tasks.add_task(webhook_notifier.send, upload_id, datetime.now(UTC))

    response.status_code = 201 if created else 200
    return UploadMetaDataCreateResponse(upload_id=upload_id, tags=result_tags)


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
    upload = upload_service.get_upload(upload_id)
    return ImageResponse(content=upload.content, media_type=upload.content_type)


@upload_router.get(
    "/{upload_id}/thumbnail",
    summary="Get image thumbnail",
    description="Download a 200px max-dimension JPEG thumbnail of an uploaded image",
    response_class=ImageResponse,
    status_code=200,
    responses={
        200: {"description": "Thumbnail image content"},
        422: {"description": "Image cannot be decoded", "model": ErrorResponse},
        **NOT_FOUND_RESPONSES,
    },
)
async def get_upload_thumbnail(
    upload_id: UploadID,
    upload_service: UploadService = Depends(get_upload_service),
    thumbnail_service: ThumbnailService = Depends(get_thumbnail_service),
):
    upload = upload_service.get_upload(upload_id)
    try:
        thumbnail = thumbnail_service.get_thumbnail(upload_id, upload.content)
    except InvalidImageException as exc:
        raise HTTPException(status_code=422, detail=exc.detail)
    return ImageResponse(content=thumbnail.content, media_type=thumbnail.content_type)


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
    thumbnail_service: ThumbnailService = Depends(get_thumbnail_service),
    _login_valid: None = Depends(check_login_valid),
):
    result = upload_service.delete_upload(upload_id)
    thumbnail_service.evict(upload_id)
    return result


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
    summary="List uploads",
    description="Get a list of uploads in descending order of upload time. "
    "Optionally filter by tags (AND logic).",
    response_model=list[UploadWithTagsResponse],
    status_code=200,
    responses={
        200: {
            "description": "List of uploads with tags and metadata",
        }
    },
)
async def list_uploads(
    tags: list[TagName] = Query(default=[], description="Filter by tags (AND logic)"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of items to return"),
    tag_service: TagService = Depends(get_tag_service),
    _login_valid: None = Depends(check_login_valid),
):
    results = tag_service.list_with_tags(tag_names=tags, offset=offset, limit=limit)
    return [UploadWithTagsResponse.from_upload_with_tags(r) for r in results]


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
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=50, description="Maximum number of items to return"),
    tag_service: TagService = Depends(get_tag_service),
    _login_valid: None = Depends(check_login_valid),
):
    tags = tag_service.list_all_tags(offset=offset, limit=limit)
    return TagListResponse(tags=tags)
