"""Menjalankan enhancement. Mode FAKE_TOPAZ=1 memakai app/fake_topaz.py.

Mode asli memanggil ffmpeg Topaz (config.TOPAZ_*), dengan batas waktu yang mematikan seluruh pohon proses.
"""

import os
import subprocess
import sys
from pathlib import Path

from app import config
from app.proc import ToolError, run_real, run_with_timeout


class TopazError(ToolError):
    pass


def is_fake_mode():
    return os.environ.get("FAKE_TOPAZ") == "1"


def run_upscale(input_path: Path, output_path: Path, timeout_sec: int):
    if not is_fake_mode():
        _run_topaz(input_path, output_path, timeout_sec)
        return

    cmd = [
        sys.executable,
        "-m",
        "app.fake_topaz",
        str(input_path),
        str(output_path),
        str(config.FAKE_TOPAZ_DELAY_SEC),
    ]
    run_real(cmd, timeout_sec, "Topaz", output_path)


def _run_topaz(input_path: Path, output_path: Path, timeout_sec: int):
    missing = [
        name
        for name, value in (
            ("TOPAZ_FFMPEG_PATH", config.TOPAZ_FFMPEG_PATH),
            ("TOPAZ_FILTER", config.TOPAZ_FILTER),
            ("TVAI_MODEL_DIR", config.TVAI_MODEL_DIR),
            ("TVAI_MODEL_DATA_DIR", config.TVAI_MODEL_DATA_DIR),
        )
        if not value
    ]
    if missing:
        raise TopazError("Topaz belum dikonfigurasi, kosong: " + ", ".join(missing))

    cmd = [
        config.TOPAZ_FFMPEG_PATH,
        "-hide_banner", "-nostdin", "-y", "-nostats",
        "-i", str(input_path),
        *config.TOPAZ_ENCODE_ARGS,
        "-filter_complex", config.TOPAZ_FILTER,
        *config.TOPAZ_ENCODE_ARGS_TAIL,
        str(output_path),
    ]
    env = {
        **os.environ,
        "TVAI_MODEL_DIR": config.TVAI_MODEL_DIR,
        "TVAI_MODEL_DATA_DIR": config.TVAI_MODEL_DATA_DIR,
    }
    try:
        returncode, stderr = run_with_timeout(cmd, env, timeout_sec)
    except OSError:
        raise TopazError("TOPAZ_FFMPEG_PATH tidak bisa dijalankan")
    except subprocess.TimeoutExpired:
        raise TopazError(f"Timeout setelah {timeout_sec} detik")

    if returncode != 0:
        # stderr berisi log ffmpeg dan path lokal: hanya ke log, bukan ke DB/UI
        print(stderr.strip(), file=sys.stderr, flush=True)
        raise TopazError("topaz gagal")
    if not output_path.exists():
        raise TopazError("Output tidak ditemukan")

