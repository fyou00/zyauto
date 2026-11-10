"""Tahap After Effects: render comp ke QuickTime (.mov) lewat aerender.

Input AE (Opsi A): sebelum render, hasil Topaz disalin ke AE_WORK_DIR/<input><ext>. File .aep tidak diubah;
template memakai footage placeholder dengan nama. Orientasi memilih template (.aep landscape atau portrait).
Mode FAKE_AE=1 memakai app/fake_ae.py (tidak membaca .aep dan tidak menyalin ke AE_WORK_DIR).
"""

import os
import shutil
from pathlib import Path

from app import config, media
from app.proc import ToolError, run_fake, run_real


class AEError(ToolError):
    pass


def is_fake_mode():
    return os.environ.get("FAKE_AE") == "1"


def run_ae(input_path, output_path, preset, timeout_sec, orientation="landscape"):
    """input_path: hasil Topaz. output_path: file .mov. preset: dict dari config.CC_PRESETS, atau None."""
    if is_fake_mode():
        run_fake("app.fake_ae", input_path, output_path, config.FAKE_AE_DELAY_SEC, timeout_sec, "AE")
        return
    _run_aerender(Path(input_path), Path(output_path), preset, timeout_sec, orientation)


def _pick_aep(preset, orientation):
    """Template sesuai orientasi video. Hanya .aep landscape yang wajib ada."""
    aep = Path(preset["aep_path"])
    if orientation == "portrait":
        candidate = aep.with_name(f"{aep.stem}_portrait{aep.suffix}")
        if candidate.is_file():
            return candidate
        raise AEError(f"AE: template portrait tidak ditemukan: {candidate.name}")
    return aep


def _stage_input(input_path):
    """Salin hasil Topaz ke AE_WORK_DIR/<input><ext>. Input lama dihapus dulu (semua AE_INPUT_STEM.*)."""
    work = Path(config.AE_WORK_DIR)
    work.mkdir(parents=True, exist_ok=True)
    for old in work.glob(f"{config.AE_INPUT_STEM}.*"):
        try:
            old.unlink()
        except OSError:
            pass
    target = work / f"{config.AE_INPUT_STEM}{input_path.suffix.lower()}"
    shutil.copyfile(input_path, target)
    return target


def _run_aerender(input_path, output_path, preset, timeout_sec, orientation):
    missing = [
        name
        for name, value in (
            ("AE_AERENDER_PATH", config.AE_AERENDER_PATH),
            ("AE_COMP_NAME", config.AE_COMP_NAME),
            ("AE_OM_TEMPLATE", config.AE_OM_TEMPLATE),
        )
        if not value
    ]
    if missing:
        raise AEError("AE belum dikonfigurasi, kosong: " + ", ".join(missing))
    if preset is None:
        raise AEError("AE: preset CC tidak ditemukan di config")

    aep_path = _pick_aep(preset, orientation)
    # Gagal dengan pesan jelas sebelum aerender dijalankan, bukan crash
    if not aep_path.is_file():
        raise AEError(f"AE: file preset tidak ditemukan: {aep_path.name}")

    # Durasi diambil dari file yang benar-benar masuk ke AE (hasil Topaz salinan), bukan tebakan
    meta = media.probe(input_path)
    _stage_input(input_path)

    cmd = [
        config.AE_AERENDER_PATH,
        "-project", str(aep_path),
        "-comp", config.AE_COMP_NAME,
        "-OMtemplate", config.AE_OM_TEMPLATE,
        "-output", str(output_path),
        "-s", "0",
        "-e", str(max(0, int(round(meta["duration"])) - 1)),
    ]
    run_real(cmd, timeout_sec, "AE", output_path)
    media.check_output(output_path, "AE")
