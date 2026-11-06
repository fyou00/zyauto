"""Menjalankan upscaling. Mode FAKE_TOPAZ=1 memakai app/fake_topaz.py.

Mode asli (Topaz) belum dikerjakan: langkah 7 di NOTES.md.
"""

import os
import subprocess
import sys
from pathlib import Path

from app import config


class TopazError(Exception):
    pass


def is_fake_mode():
    return os.environ.get("FAKE_TOPAZ") == "1"


def run_upscale(input_path: Path, output_path: Path, timeout_sec: int):
    if not is_fake_mode():
        raise TopazError("Topaz belum dikonfigurasi")

    cmd = [
        sys.executable,
        "-m",
        "app.fake_topaz",
        str(input_path),
        str(output_path),
        str(config.FAKE_TOPAZ_DELAY_SEC),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        raise TopazError(f"Timeout setelah {timeout_sec} detik")

    if result.returncode != 0:
        # stderr berisi traceback dan path lokal: hanya ke log, bukan ke DB/UI
        print(result.stderr.strip(), file=sys.stderr, flush=True)
        raise TopazError("fake topaz gagal")
    if not output_path.exists():
        raise TopazError("Output tidak ditemukan")
