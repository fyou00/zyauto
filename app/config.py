"""Semua path dan setting prototype. Jangan hardcode nilai ini di file lain."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path):
    """Baca .env sederhana (KEY=VALUE) tanpa library. Env yang sudah ada tidak ditimpa."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


_load_dotenv(BASE_DIR / ".env")
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "outputs"
DB_PATH = DATA_DIR / "app.sqlite"
TEMPLATE_DIR = BASE_DIR / "app" / "templates"
STATIC_DIR = BASE_DIR / "app" / "static"

# Upload
ALLOWED_EXTS = ("mp4", "mov", "mkv")
MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MB

# Worker
MAX_ATTEMPTS = 2                 # percobaan maksimal per job (termasuk percobaan pertama)
JOB_TIMEOUT_SEC = 25 * 60        # 25 menit per job
POLL_INTERVAL_SEC = 3            # interval polling status di halaman (HTMX)

# Mode FAKE: worker menjalankan app/fake_topaz.py sebagai pengganti Topaz
FAKE_TOPAZ_DELAY_SEC = 5

# Topaz asli (langkah 7). Nilai diisi user di .env (lihat .env.example). JANGAN diisi tebakan di sini.
TOPAZ_FFMPEG_PATH = os.environ.get("TOPAZ_FFMPEG_PATH", "")  # path ffmpeg dari Topaz Video AI
TOPAZ_FILTER = os.environ.get("TOPAZ_FILTER", "")            # string -filter_complex dari Topaz
TVAI_MODEL_DIR = os.environ.get("TVAI_MODEL_DIR", "")
TVAI_MODEL_DATA_DIR = os.environ.get("TVAI_MODEL_DATA_DIR", "")

# Opsi encode Topaz, urutan persis dari command manual yang sudah jalan di Windows.
# Di antara TOPAZ_ENCODE_ARGS dan TOPAZ_ENCODE_ARGS_TAIL: "-filter_complex", TOPAZ_FILTER.
TOPAZ_ENCODE_ARGS = [
    "-sws_flags", "spline+accurate_rnd+full_chroma_int",
    "-color_trc", "2", "-colorspace", "2", "-color_primaries", "2",
]
TOPAZ_ENCODE_ARGS_TAIL = [
    "-c:v", "h264_nvenc", "-profile:v", "high", "-preset", "medium",
    "-pix_fmt", "yuv420p", "-b:v", "0",
    "-map_metadata", "0",
    "-movflags", "frag_keyframe+empty_moov+delay_moov+use_metadata_tags+write_colr",
    "-map_metadata:s:v", "0:s:v", "-map_metadata:s:a", "0:s:a",
    "-c:a", "copy",
]
