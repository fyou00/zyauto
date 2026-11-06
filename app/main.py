"""Route FastAPI: halaman upload dan pembuatan job."""

import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import config, db

templates = Jinja2Templates(directory=config.TEMPLATE_DIR)
CHUNK_BYTES = 1024 * 1024


@asynccontextmanager
async def lifespan(app):
    db.init_db()
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


@app.get("/jobs", response_class=HTMLResponse)
def list_jobs(request: Request):
    return templates.TemplateResponse(
        request,
        "_jobs.html",
        {"jobs": db.list_jobs(), "poll_sec": config.POLL_INTERVAL_SEC},
    )


@app.post("/jobs")
async def create_job(file: UploadFile = File(...)):
    original_name = Path(file.filename or "").name
    ext = Path(original_name).suffix.lower().lstrip(".")
    if ext not in config.ALLOWED_EXTS:
        raise HTTPException(400, "Format harus mp4, mov, atau mkv")

    job_id = str(uuid.uuid4())
    input_path = config.UPLOAD_DIR / f"{job_id}.{ext}"
    size = 0
    saved = False
    try:
        with input_path.open("wb") as out:
            while chunk := await file.read(CHUNK_BYTES):
                size += len(chunk)
                if size > config.MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "Ukuran file melebihi batas")
                out.write(chunk)
        saved = True
    finally:
        if not saved:
            input_path.unlink(missing_ok=True)

    db.create_job(job_id, original_name, ext, input_path, size)
    return RedirectResponse("/", status_code=303)
