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
INTERMEDIATE_DIR = DATA_DIR / "intermediates"  # file perantara Topaz/AE, dihapus setelah job selesai
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

# Kolom "Waktu render" di daftar job. HANYA untuk testing: aktif jika SHOW_RENDER_TIME=1 di .env.
# Default mati, jadi di produksi user tidak melihat kolom ini (tidak dirender sama sekali).
SHOW_RENDER_TIME = os.environ.get("SHOW_RENDER_TIME") == "1"

# Mode FAKE: worker menjalankan app/fake_topaz.py sebagai pengganti Topaz
FAKE_TOPAZ_DELAY_SEC = 5

# Layanan yang tersedia. topaz_cc butuh preset CC.
SERVICES = ("topaz_only", "topaz_cc")

# Preset CC. id stabil (dipakai di DB dan form), label untuk UI, aep_path = template .aep.
# aep_file = nama file di AE_PRESET_DIR. AE_PRESET_DIR dari .env; kosong -> BASE_DIR / "presets".
# File .aep TIDAK di-commit (presets/ ada di .gitignore). FAKE_AE tidak membaca aep_path sama sekali.
AE_PRESET_DIR = Path(os.environ.get("AE_PRESET_DIR") or BASE_DIR / "presets")
_PRESET_FILES = (
    ("soft_fresh", "CC Soft Fresh", "soft_fresh.aep"),
    ("dream_glow", "CC Dream Glow", "dream_glow.aep"),
    ("blue_beats", "CC Blue Beats", "blue_beats.aep"),
    ("warm_pop", "CC Warm Pop", "warm_pop.aep"),
    ("punchy_contrast", "CC Punchy Contrast", "punchy_contrast.aep"),
)
CC_PRESETS = [
    {"id": pid, "label": label, "aep_path": AE_PRESET_DIR / filename}
    for pid, label, filename in _PRESET_FILES
]


def get_cc_preset(preset_id):
    """Mengembalikan dict preset dengan id tersebut, atau None."""
    for preset in CC_PRESETS:
        if preset["id"] == preset_id:
            return preset
    return None

# Mode FAKE AE dan HandBrake: tahap menyalin file saja (tes di macOS). Delay dibaca dari .env.
FAKE_AE_DELAY_SEC = float(os.environ.get("FAKE_AE_DELAY_SEC", "5"))
FAKE_HANDBRAKE_DELAY_SEC = float(os.environ.get("FAKE_HANDBRAKE_DELAY_SEC", "5"))

# After Effects asli. Nilai diisi user di .env (lihat .env.example). JANGAN diisi tebakan di sini.
AE_AERENDER_PATH = os.environ.get("AE_AERENDER_PATH", "")  # path aerender.exe
AE_COMP_NAME = os.environ.get("AE_COMP_NAME", "")          # nama comp di template .aep
AE_OM_TEMPLATE = os.environ.get("AE_OM_TEMPLATE", "")      # nama output module QuickTime

# HandBrakeCLI (tahap encoding topaz_cc). Nilai diisi user di .env.
HANDBRAKE_CLI_PATH = os.environ.get("HANDBRAKE_CLI_PATH", "")
HANDBRAKE_PRESET_FILE = os.environ.get("HANDBRAKE_PRESET_FILE", "")  # file .json export HandBrake (NVENC)
HANDBRAKE_PRESET_NAME = os.environ.get("HANDBRAKE_PRESET_NAME", "")

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
