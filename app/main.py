"""Route FastAPI: halaman upload dan pembuatan job."""

import re
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
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


UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


@app.get("/jobs/{job_id}/download")
def download_job(job_id: str):
    job = db.get_job(job_id)
    if job is None or job["status"] != "done" or not job["output_path"]:
        raise HTTPException(404, "Hasil belum tersedia")
    output_path = Path(job["output_path"])
    if not output_path.is_file():
        raise HTTPException(404, "Hasil belum tersedia")
    stem = UNSAFE_CHARS.sub("_", Path(job["original_name"]).stem).strip("._") or "video"
    return FileResponse(
        output_path,
        filename=f"upscaled_{stem}{output_path.suffix}",  # topaz_cc keluar sebagai .mp4 dari HandBrake
        media_type="application/octet-stream",
    )


@app.get("/ui/cc-presets", response_class=HTMLResponse)
def cc_preset_field(request: Request, service: str = ""):
    """Fragment HTMX: dropdown preset hanya untuk topaz_cc."""
    return templates.TemplateResponse(
        request,
        "_preset.html",
        {"service": service, "presets": config.CC_PRESETS},
    )


def validate_service(service: str, cc_preset: str):
    """Validasi di server (wajib, form bisa dikirim dengan nilai apa pun).

    Mengembalikan cc_preset yang valid, atau None untuk topaz_only.
    """
    if service not in config.SERVICES:
        raise HTTPException(400, "Pilih layanan (topaz_only atau topaz_cc)")
    if service == "topaz_only":
        return None
    if not cc_preset:
        raise HTTPException(400, "Pilih preset CC untuk layanan topaz_cc")
    if config.get_cc_preset(cc_preset) is None:
        raise HTTPException(400, "Preset tidak dikenal")
    return cc_preset


@app.post("/jobs")
async def create_job(
    file: UploadFile = File(...),
    service: str = Form(""),
    cc_preset: str = Form(""),
):
    original_name = Path(file.filename or "").name
    ext = Path(original_name).suffix.lower().lstrip(".")
    if ext not in config.ALLOWED_EXTS:
        raise HTTPException(400, "Format harus mp4, mov, atau mkv")
    # Validasi layanan dan preset sebelum file disimpan, supaya tidak ada file yatim
    cc_preset = validate_service(service, cc_preset)

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

    db.create_job(job_id, original_name, ext, input_path, size, service, cc_preset)
    return RedirectResponse("/", status_code=303)
