"""Tahap encoding akhir: HandBrakeCLI (.mov -> .mp4) memakai preset NVENC dari file .json.

Mode FAKE_HANDBRAKE=1 memakai app/fake_handbrake.py. Hanya topaz_cc yang melewati tahap ini.
"""

import json
import os
from pathlib import Path

from app import config
from app.proc import ToolError, run_fake, run_real

LABEL = "HandBrake"


class HandBrakeError(ToolError):
    pass


def is_fake_mode():
    return os.environ.get("FAKE_HANDBRAKE") == "1"


def run_encode(input_path, output_path, timeout_sec):
    if is_fake_mode():
        run_fake("app.fake_handbrake", input_path, output_path,
                 config.FAKE_HANDBRAKE_DELAY_SEC, timeout_sec, LABEL)
        return

    missing = [
        name
        for name, value in (
            ("HANDBRAKE_CLI_PATH", config.HANDBRAKE_CLI_PATH),
            ("HANDBRAKE_PRESET_FILE", config.HANDBRAKE_PRESET_FILE),
            ("HANDBRAKE_PRESET_NAME", config.HANDBRAKE_PRESET_NAME),
        )
        if not value
    ]
    if missing:
        raise HandBrakeError("HandBrake belum dikonfigurasi, kosong: " + ", ".join(missing))
    _check_nvenc_preset()

    cmd = [
        config.HANDBRAKE_CLI_PATH,
        "-i", str(input_path),
        "-o", str(output_path),
        "--preset-import-file", config.HANDBRAKE_PRESET_FILE,
        "-Z", config.HANDBRAKE_PRESET_NAME,
    ]
    run_real(cmd, timeout_sec, LABEL, output_path)


def _check_nvenc_preset():
    """Preset wajib memakai encoder NVENC. Dibaca dari file export HandBrake."""
    try:
        data = json.loads(Path(config.HANDBRAKE_PRESET_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise HandBrakeError("HandBrake: file preset tidak bisa dibaca")
    preset = _find_preset(data.get("PresetList", []), config.HANDBRAKE_PRESET_NAME)
    if preset is None:
        raise HandBrakeError("HandBrake: preset tidak ditemukan di file preset")
    if not str(preset.get("VideoEncoder", "")).startswith("nvenc"):
        raise HandBrakeError("HandBrake: preset bukan NVENC, tahap encoding belum siap")


def _find_preset(items, name):
    """Cari preset berdasarkan nama, termasuk di dalam folder (ChildrenArray)."""
    for item in items:
        if item.get("PresetName") == name:
            return item
        found = _find_preset(item.get("ChildrenArray", []), name)
        if found is not None:
            return found
    return None
