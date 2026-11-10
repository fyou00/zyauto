"""Baca metadata video lewat ffprobe (durasi dan orientasi)."""

import json
from pathlib import Path

from app import config
from app.proc import ToolError, run_capture


class MediaError(ToolError):
    pass


def probe(path):
    """Mengembalikan dict: duration (detik, float) dan orientation ('landscape'|'portrait').

    ffprobe diasumsikan ada di folder yang sama dengan TOPAZ_FFMPEG_PATH (paket Topaz Video AI).
    """
    ffmpeg = Path(config.TOPAZ_FFMPEG_PATH) if config.TOPAZ_FFMPEG_PATH else None
    if ffmpeg is None:
        raise MediaError("ffprobe butuh TOPAZ_FFMPEG_PATH (folder yang sama dengan ffprobe.exe)")
    ffprobe = ffmpeg.with_name("ffprobe.exe" if ffmpeg.suffix.lower() == ".exe" else "ffprobe")
    if not ffprobe.is_file():
        raise MediaError("ffprobe tidak ditemukan di folder ffmpeg Topaz")

    cmd = [
        str(ffprobe), "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height:format=duration",
        "-of", "json",
        str(path),
    ]
    raw = run_capture(cmd, 60, "ffprobe")
    try:
        data = json.loads(raw)
        stream = data["streams"][0]
        width, height = int(stream["width"]), int(stream["height"])
        duration = float(data["format"]["duration"])
    except (ValueError, KeyError, IndexError, TypeError):
        raise MediaError("ffprobe: metadata video tidak terbaca")
    if duration <= 0:
        raise MediaError("ffprobe: durasi video tidak valid")
    return {
        "duration": duration,
        "orientation": "landscape" if width >= height else "portrait",
    }


def check_output(path, label):
    """Hasil tahap asli (aerender/HandBrake) harus video dengan durasi > 0. Kalau tidak, tahap gagal."""
    try:
        probe(path)
    except ToolError as e:
        raise MediaError(f"{label}: output tidak valid ({e})")
