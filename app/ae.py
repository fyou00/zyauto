"""Tahap After Effects: render comp ke QuickTime (.mov) lewat aerender.

Mode FAKE_AE=1 memakai app/fake_ae.py. Mode asli butuh nilai di .env (lihat config.py).
"""

import os

from app import config
from app.proc import ToolError, run_fake


class AEError(ToolError):
    pass


def is_fake_mode():
    return os.environ.get("FAKE_AE") == "1"


def run_ae(input_path, output_path, preset, timeout_sec):
    """input_path: hasil Topaz. output_path: file .mov. preset: dict dari config.CC_PRESETS, atau None."""
    if is_fake_mode():
        run_fake("app.fake_ae", input_path, output_path, config.FAKE_AE_DELAY_SEC, timeout_sec, "AE")
        return
    _run_aerender(input_path, output_path, preset, timeout_sec)


def _run_aerender(input_path, output_path, preset, timeout_sec):
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
    # BELUM DIPUTUSKAN: cara memasukkan hasil Topaz (input_path) ke comp.
    # Tanpa itu aerender merender footage bawaan template dan hasilnya salah diam-diam,
    # jadi mode asli sengaja dihentikan di sini sampai keputusan diambil.
    raise AEError("AE asli belum siap: input hasil Topaz belum dipetakan ke comp")
