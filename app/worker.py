"""Worker: jalankan terus, ambil satu job per waktu.

Jalankan: python -m app.worker  (set FAKE_TOPAZ=1 untuk tes tanpa GPU)
"""

import time
from pathlib import Path

from app import config, db
from app.topaz import TopazError, run_upscale


def process_job(job):
    output_path = config.OUTPUT_DIR / f"{job['id']}.{job['ext']}"
    try:
        run_upscale(Path(job["input_path"]), output_path, config.JOB_TIMEOUT_SEC)
    except TopazError as e:
        db.mark_failed(job["id"], str(e))
        print(f"job {job['id']} failed: {e}", flush=True)
        return
    except Exception as e:  # error tak terduga: tandai failed, worker tetap hidup
        db.mark_failed(job["id"], f"error tak terduga: {type(e).__name__}")
        print(f"job {job['id']} failed (unexpected): {e!r}", flush=True)
        return
    db.mark_done(job["id"], output_path)
    print(f"job {job['id']} done", flush=True)


def main():
    db.init_db()
    requeued, failed = db.reset_processing_jobs()
    if requeued or failed:
        print(f"recovery: {requeued} dikembalikan ke queued, {failed} ditandai failed", flush=True)
    print("worker start", flush=True)
    while True:
        job = db.claim_next_job()
        if job is None:
            time.sleep(config.POLL_INTERVAL_SEC)
            continue
        print(f"job {job['id']} processing", flush=True)
        process_job(job)


if __name__ == "__main__":
    main()
