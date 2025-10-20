from contextlib import asynccontextmanager

import fastapi
from fastapi import Depends, File, HTTPException, UploadFile
from sqlmodel import Session, create_engine

from lenzr_server import models
from lenzr_server.file_storages.on_disk_file_storage import (
    OnDiskFileStorage,
)
from lenzr_server.schemas import (
    ErrorResponse,
    ImageResponse,
    UploadResponse,
    UploadsListResponse,
)
from lenzr_server.types import UploadID
from lenzr_server.upload_id_creators.hashing_id_creator import HashingIDCreator
from lenzr_server.upload_id_creators.id_creator import IDCreator
from lenzr_server.upload_service import AlreadyExistingException, NotFoundException, UploadService

sqlite_file_name = "/tmp/lenzr_server_db.sqlite3"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


@asynccontextmanager
async def db_lifetime(_app: fastapi.FastAPI):
    models.SQLModel.metadata.create_all(engine)
    yield
    models.SQLModel.metadata.drop_all(engine)


app = fastapi.FastAPI(
    title="Lenzr Server",
    lifespan=db_lifetime,
)


def get_id_creator():
    creator = HashingIDCreator(seed=32)
    return creator


def get_file_storage():
    file_storage = OnDiskFileStorage(base_path="/tmp/lenzr_server")
    return file_storage


def get_db_session():
    with Session(engine) as session:
        yield session


def get_upload_service(
    file_storage: OnDiskFileStorage = Depends(get_file_storage),
    db_session: Session = Depends(get_db_session),
    upload_id_creator: IDCreator = Depends(get_id_creator),
):
    upload_service = UploadService(
        file_storage=file_storage,
        database_session=db_session,
        upload_id_creator=upload_id_creator,
    )
    return upload_service


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
        400: {"description": "Bad request - invalid file", "model": ErrorResponse},
        409: {"description": "Upload already exists", "model": ErrorResponse},
    },
)
async def upload_file(
    upload: UploadFile = File(..., description="Image file to upload", media_type="image/*"),
    upload_service: UploadService = Depends(get_upload_service),
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


@app.get(
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
async def list_uploads(
    upload_service: UploadService = Depends(get_upload_service),
):
    ids = upload_service.list_uploads()

    return UploadsListResponse(uploads=list(ids))
