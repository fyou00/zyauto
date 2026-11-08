"""Tes aturan antrian dalam mode FAKE (tanpa GPU, tanpa AE, tanpa HandBrake).

Jalankan dari root repo: python tests_queue.py

Setiap skenario berjalan di salinan app/ dalam folder sementara, jadi data/ dan DB asli tidak tersentuh.
Yang dibuktikan: satu job selesai penuh (termasuk tahap AE dan encoding) sebelum job berikutnya mulai.
"""

import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PRESET_ID = "uji_cc"
# Preset uji ditambahkan di AKHIR salinan config.py (menimpa CC_PRESETS repo), bukan di config repo
CC_PRESETS_LINE = (
    '\n# override untuk tes\nCC_PRESETS = [{"id": "' + PRESET_ID + '", "label": "CC Uji", '
    '"aep_path": BASE_DIR / "presets" / "uji.aep"}]\n'
)


def now(offset_sec=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_sec)).isoformat(timespec="seconds")


def build_copy(tmp):
    """Salin app/ ke tmp dan isi CC_PRESETS di salinan config.py."""
    shutil.copytree(BASE_DIR / "app", tmp / "app",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    cfg = tmp / "app" / "config.py"
    text = cfg.read_text(encoding="utf-8")
    cfg.write_text(text + CC_PRESETS_LINE, encoding="utf-8")


def insert_jobs(tmp, jobs):
    """created_at berurutan (1 detik) supaya urutan antrian pasti."""
    conn = sqlite3.connect(tmp / "data" / "app.sqlite")
    for i, job in enumerate(jobs):
        src = tmp / "data" / "uploads" / f"{job['id']}.{job['ext']}"
        src.write_bytes(b"video-" + job["id"].encode())
        conn.execute(
            "INSERT INTO jobs (id, original_name, ext, input_path, size_bytes, status, created_at, "
            "service, cc_preset) VALUES (?, ?, ?, ?, ?, 'queued', ?, ?, ?)",
            (job["id"], f"{job['id']}.{job['ext']}", job["ext"], str(src),
             src.stat().st_size, now(i), job["service"], job.get("cc_preset")),
        )
    conn.commit()
    conn.close()


def wait_terminal(tmp, job_ids, timeout_sec=60):
    """Tunggu semua job keluar dari queued/processing."""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        conn = sqlite3.connect(tmp / "data" / "app.sqlite")
        rows = conn.execute(
            f"SELECT status FROM jobs WHERE id IN ({','.join('?' * len(job_ids))})", job_ids
        ).fetchall()
        conn.close()
        if all(status in ("done", "failed") for (status,) in rows):
            return True
        time.sleep(0.5)
    return False


def fetch_rows(tmp):
    conn = sqlite3.connect(tmp / "data" / "app.sqlite")
    conn.row_factory = sqlite3.Row
    rows = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM jobs")}
    conn.close()
    return rows


def run_scenario(name, jobs, extra_env, expect):
    """jobs: [job1 (topaz_cc), job2 (topaz_only)]. expect: [(job_id, status_akhir)]. Mengembalikan (lulus, tmp)."""
    tmp = Path(tempfile.mkdtemp())
    build_copy(tmp)
    env = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "FAKE_TOPAZ": "1",
        "FAKE_AE": "1",
        "FAKE_HANDBRAKE": "1",
        "FAKE_AE_DELAY_SEC": "2",
        "FAKE_HANDBRAKE_DELAY_SEC": "2",
        **extra_env,
    }
    subprocess.run([sys.executable, "-c", "from app import db; db.init_db()"],
                   cwd=tmp, env=env, check=True)
    insert_jobs(tmp, jobs)
    ids = [j["id"] for j in jobs]

    log_path = tmp / "worker.log"
    with log_path.open("w", encoding="utf-8") as fh:
        worker = subprocess.Popen([sys.executable, "-m", "app.worker"], cwd=tmp, env=env,
                                  stdout=fh, stderr=subprocess.STDOUT)
        try:
            finished = wait_terminal(tmp, ids)
        finally:
            worker.terminate()
            worker.wait(timeout=10)

    log = log_path.read_text(encoding="utf-8")
    lines = [ln for ln in log.splitlines() if ln.startswith("[")]
    rows = fetch_rows(tmp)
    results = []

    def check(cond, msg):
        results.append(bool(cond))
        print(("  OK    " if cond else "  GAGAL ") + msg)

    def pos(text):
        return next((i for i, ln in enumerate(lines) if text in ln), -1)

    print(f"\n=== {name} ===")
    print("\n".join(lines))
    print("--- cek")
    check(finished, "semua job sampai status akhir")
    for job_id, status in expect:
        check(rows[job_id]["status"] == status,
              f"{job_id}: status {rows[job_id]['status']} (harap {status})")

    first, second = jobs[0]["id"], jobs[1]["id"]
    f_fin, s_start = rows[first]["finished_at"], rows[second]["started_at"]
    check(bool(f_fin and s_start and s_start >= f_fin),
          f"job 2 mulai ({s_start}) setelah job 1 selesai ({f_fin})")

    end1 = max(pos(f"job {first} done"), pos(f"job {first} failed"))
    start2 = pos(f"job {second} processing")
    check(end1 >= 0 and start2 > end1, "log: 'processing' job 2 muncul setelah job 1 done/failed")

    if jobs[0]["service"] == "topaz_cc":
        stages = [pos(f"job {first} stage {s} start") for s in ("topaz", "ae", "encoding")]
        if expect[0][1] == "done":
            check(all(p >= 0 for p in stages) and stages == sorted(stages),
                  "job 1: tahap topaz -> ae -> encoding berurutan di log")
        else:
            check(stages[0] >= 0 and stages[1] >= 0 and stages[2] == -1,
                  "job 1 gagal di AE: tahap encoding tidak dimulai")

    left = sorted(p.name for p in (tmp / "data" / "intermediates").glob("*"))
    check(not left, f"tidak ada file perantara tersisa {left}")
    check(all(rows[i]["intermediate_path"] is None and rows[i]["stage"] is None for i in ids),
          "intermediate_path dan stage kosong di semua job")

    for job_id, status in expect:
        if status != "done":
            continue
        job = next(j for j in jobs if j["id"] == job_id)
        ext = "mp4" if job["service"] == "topaz_cc" else job["ext"]
        out = tmp / "data" / "outputs" / f"{job_id}.{ext}"
        same = out.is_file() and out.read_bytes() == Path(rows[job_id]["input_path"]).read_bytes()
        check(same, f"output {out.name} ada dan identik dengan input")

    return all(results), tmp


JOBS = [
    {"id": "job1", "ext": "mov", "service": "topaz_cc", "cc_preset": PRESET_ID},
    {"id": "job2", "ext": "mp4", "service": "topaz_only"},
]


def main():
    ok_a, _ = run_scenario(
        "A: order 1 topaz_cc, order 2 topaz_only (semua sukses)",
        [dict(j) for j in JOBS], {}, [("job1", "done"), ("job2", "done")],
    )
    ok_b, _ = run_scenario(
        "B: AE job 1 gagal -> job 1 failed, job 2 tetap jalan",
        [dict(j) for j in JOBS], {"FAKE_AE_FAIL": "1"}, [("job1", "failed"), ("job2", "done")],
    )
    print("\n=== RINGKASAN ===")
    print(f"skenario A: {'LULUS' if ok_a else 'GAGAL'}")
    print(f"skenario B: {'LULUS' if ok_b else 'GAGAL'}")
    sys.exit(0 if (ok_a and ok_b) else 1)


if __name__ == "__main__":
    main()
