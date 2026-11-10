"""Proses eksternal dengan batas waktu yang mematikan seluruh pohon proses.

Dipakai oleh tahap Topaz, AE, dan HandBrake. Harus jalan di Windows dan macOS.
"""

import os
import signal
import subprocess
import sys
from pathlib import Path


class ToolError(Exception):
    """Gagal di salah satu tahap pipeline. Pesan boleh tampil di UI (tanpa path lokal atau stderr)."""


# Proses yang sedang berjalan. Dipakai kill_active() saat worker dihentikan (Ctrl+C / SIGTERM),
# supaya aerender/ffmpeg/HandBrake tidak tertinggal sebagai proses yatim.
_active = set()


def start(cmd, env, capture_stdout=False):
    """Menjalankan proses. Melempar OSError jika executable tidak bisa dijalankan."""
    kwargs = {}
    if os.name != "nt":
        kwargs["start_new_session"] = True  # pgid = pid, supaya seluruh grup bisa dibunuh
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE if capture_stdout else subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        **kwargs,
    )
    _active.add(proc)
    return proc


def kill_active():
    """Bunuh seluruh pohon proses semua tahap yang sedang berjalan. Aman dipanggil dari signal handler."""
    for proc in list(_active):
        if proc.poll() is None:
            kill_tree(proc)


def kill_tree(proc):
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
        return
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def run_with_timeout(cmd, env, timeout_sec):
    """Mengembalikan (returncode, stderr).

    Setelah timeout, seluruh pohon proses dibunuh lalu subprocess.TimeoutExpired dilempar.
    """
    proc = start(cmd, env)
    try:
        _, stderr = proc.communicate(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        kill_tree(proc)
        proc.communicate()
        raise
    finally:
        _active.discard(proc)
    return proc.returncode, stderr


def run_capture(cmd, timeout_sec, label):
    """Menjalankan tool dan mengembalikan stdout. Timeout tetap membunuh seluruh pohon proses."""
    try:
        proc = start(cmd, None, capture_stdout=True)
    except OSError:
        raise ToolError(f"{label} tidak bisa dijalankan")
    try:
        stdout, stderr = proc.communicate(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        kill_tree(proc)
        proc.communicate()
        raise ToolError(f"{label}: timeout setelah {timeout_sec} detik")
    finally:
        _active.discard(proc)
    if proc.returncode != 0:
        print(stderr.strip(), file=sys.stderr, flush=True)
        raise ToolError(f"{label} gagal")
    return stdout


def run_real(cmd, timeout_sec, label, output_path):
    """Menjalankan tool asli. Gagal -> ToolError berlabel tahap. Stderr hanya ke log."""
    try:
        returncode, stderr = run_with_timeout(cmd, None, timeout_sec)
    except OSError:
        raise ToolError(f"{label} tidak bisa dijalankan")
    except subprocess.TimeoutExpired:
        raise ToolError(f"{label}: timeout setelah {timeout_sec} detik")
    if returncode != 0:
        print(stderr.strip(), file=sys.stderr, flush=True)
        raise ToolError(f"{label} gagal")
    if not Path(output_path).exists():
        raise ToolError(f"{label}: output tidak ditemukan")


def run_fake(module, src, dst, delay_sec, timeout_sec, label):
    """Pengganti tool asli: app.<module> sebagai subprocess. Timeout tetap membunuh seluruh pohon proses."""
    cmd = [sys.executable, "-m", module, str(src), str(dst), str(delay_sec)]
    run_real(cmd, timeout_sec, label, dst)
