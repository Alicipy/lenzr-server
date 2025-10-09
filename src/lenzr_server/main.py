import fastapi
from fastapi import File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response

app = fastapi.FastAPI(
    title="Lenzr Server",
)

STORE: dict[str, tuple[bytes, str]] = {}

@app.put("/uploads")
async def upload_file(upload: UploadFile = File(...)):
    content = await upload.read()
    content_type = upload.content_type
    if content_type is None or not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Bad request - invalid file")

    upload_id = str(len(STORE) + 1)
    STORE[upload_id] = (content, content_type)

    return JSONResponse(status_code=201, content={"upload_id": upload_id, })

@app.get("/uploads/{upload_id}")
async def get_upload(upload_id: str):
    if upload_id not in STORE:
        raise HTTPException(status_code=404, detail="Upload not found")

    content, content_type = STORE[upload_id]
    return Response(content=content, media_type=content_type)

@app.get("/uploads")
async def list_uploads():
    return JSONResponse(content={"uploads": list(STORE.keys())})