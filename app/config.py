"""Semua path dan setting prototype. Jangan hardcode nilai ini di file lain."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
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

# Topaz asli (langkah 7). Diisi user dari aplikasi Topaz. JANGAN diisi tebakan.
TOPAZ_FFMPEG_PATH = ""   # TODO user: path ffmpeg.exe dari Topaz Video AI
TOPAZ_FILTER = ""        # TODO user: parameter filter dari Topaz
# Env TVAI_* juga diisi user pada langkah 7.
