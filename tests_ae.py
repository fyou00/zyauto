"""Tes verifikasi output tahap AE dan HandBrake dalam mode asli. aerender dan HandBrakeCLI diganti stub.

Jalankan dari root repo: python tests_ae.py
Butuh ffmpeg dan ffprobe (Mac: /opt/local/bin). Tidak butuh After Effects atau HandBrake.
Yang dibuktikan:
  - output 0 byte / tidak valid -> tahap gagal dengan pesan jelas (bukan done)
  - output valid -> lolos, argumen -s/-e sesuai durasi input
  - stderr tool tetap tercatat walau sukses
Setiap skenario berjalan di folder sementara; data/ dan DB asli tidak tersentuh.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Stub: menulis argumen ke STUB_ARGS_FILE, lalu sesuai STUB_MODE:
#   valid -> salin STUB_SRC ke output; empty -> output 0 byte; warn -> sama seperti valid + warning di stderr
STUB_TEMPLATE = """#!{python}
import os
import shutil
import sys

args = sys.argv[1:]
out = args[args.index("-output") + 1] if "-output" in args else args[args.index("-o") + 1]
with open(os.environ["STUB_ARGS_FILE"], "w", encoding="utf-8") as fh:
    fh.write("\\n".join(args))
mode = os.environ.get("STUB_MODE", "valid")
if mode == "warn":
    print("WARN_TEST footage missing", file=sys.stderr)
if mode == "empty":
    open(out, "wb").close()
else:
    shutil.copyfile(os.environ["STUB_SRC"], out)
"""

AE_SNIPPET = """
from pathlib import Path
from app import config
from app.ae import run_ae
from app.proc import ToolError
try:
    run_ae(Path("src.mp4"), Path("out.mov"), config.CC_PRESETS[0], 60, "landscape")
    print("RESULT ok")
except ToolError as e:
    print("RESULT err " + str(e))
"""

HB_SNIPPET = """
from pathlib import Path
from app.handbrake import run_encode
from app.proc import ToolError
try:
    run_encode(Path("in.mov"), Path("out.mp4"), 60)
    print("RESULT ok")
except ToolError as e:
    print("RESULT err " + str(e))
"""


def make_video(path, seconds, ffmpeg):
    subprocess.run(
        [ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i",
         f"testsrc=duration={seconds}:size=320x240:rate=25", "-c:v", "mpeg4", str(path)],
        check=True,
    )


def setup(tmp, mode, ffmpeg):
    (tmp / "presets").mkdir()
    (tmp / "presets" / "soft_fresh.aep").write_bytes(b"dummy-aep")
    make_video(tmp / "src.mp4", 3, ffmpeg)
    shutil.copyfile(tmp / "src.mp4", tmp / "in.mov")
    stub = STUB_TEMPLATE.replace("{python}", sys.executable)
    for name in ("aerender", "handbrakecli"):
        path = tmp / name
        path.write_text(stub, encoding="utf-8")
        path.chmod(0o755)
    preset = {"PresetList": [{"PresetName": "uji_nvenc", "VideoEncoder": "nvenc_h264"}]}
    (tmp / "hb.json").write_text(json.dumps(preset), encoding="utf-8")
    return {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(BASE_DIR),
        "PYTHONDONTWRITEBYTECODE": "1",
        "FAKE_AE": "",
        "FAKE_HANDBRAKE": "",
        "TOPAZ_FFMPEG_PATH": ffmpeg,
        "AE_AERENDER_PATH": str(tmp / "aerender"),
        "AE_COMP_NAME": "Comp 1",
        "AE_OM_TEMPLATE": "QuickTime",
        "AE_PRESET_DIR": str(tmp / "presets"),
        "AE_WORK_DIR": str(tmp / "ae_work"),
        "HANDBRAKE_CLI_PATH": str(tmp / "handbrakecli"),
        "HANDBRAKE_PRESET_FILE": str(tmp / "hb.json"),
        "HANDBRAKE_PRESET_NAME": "uji_nvenc",
        "STUB_SRC": str(tmp / "src.mp4"),
        "STUB_ARGS_FILE": str(tmp / "args.txt"),
        "STUB_MODE": mode,
    }


def scenario(mode, which, ffmpeg):
    """Jalankan satu tahap dengan stub. Mengembalikan (stdout, stderr, daftar argumen aerender/HandBrake)."""
    tmp = Path(tempfile.mkdtemp())
    try:
        env = setup(tmp, mode, ffmpeg)
        code = AE_SNIPPET if which == "ae" else HB_SNIPPET
        proc = subprocess.run(
            [sys.executable, "-c", code], cwd=tmp, env=env,
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
        )
        args_file = tmp / "args.txt"
        args = args_file.read_text(encoding="utf-8").split("\n") if args_file.exists() else []
        return proc.stdout, proc.stderr, args
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def arg_value(args, flag):
    if flag in args and args.index(flag) + 1 < len(args):
        return args[args.index(flag) + 1]
    return None


def main():
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        print("ffmpeg tidak ditemukan di PATH. Tes ini butuh ffmpeg dan ffprobe.")
        sys.exit(2)

    results = []

    def check(cond, msg):
        results.append(bool(cond))
        print(("  OK    " if cond else "  GAGAL ") + msg)

    print("AE (aerender stub, mode asli)")
    out, _, _ = scenario("empty", "ae", ffmpeg)
    check("RESULT err AE: output tidak valid" in out, "output 0 byte -> gagal dengan pesan jelas")

    out, _, args = scenario("valid", "ae", ffmpeg)
    check("RESULT ok" in out, "output valid -> lolos")
    check(arg_value(args, "-s") == "0" and arg_value(args, "-e") == "2",
          f"input 3 detik -> -s 0 -e 2 (dapat -s {arg_value(args, '-s')} -e {arg_value(args, '-e')})")

    out, err, _ = scenario("warn", "ae", ffmpeg)
    check("RESULT ok" in out and "[AE] WARN_TEST" in err, "stderr tool sukses tetap masuk log")

    print("HandBrake (HandBrakeCLI stub, mode asli)")
    out, _, _ = scenario("empty", "hb", ffmpeg)
    check("RESULT err HandBrake: output tidak valid" in out, "output 0 byte -> gagal dengan pesan jelas")

    out, _, _ = scenario("valid", "hb", ffmpeg)
    check("RESULT ok" in out, "output valid -> lolos")

    print("\n=== RINGKASAN ===")
    ok = all(results)
    print(f"tes AE/HandBrake output: {'LULUS' if ok else 'GAGAL'} ({sum(results)}/{len(results)} cek)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
