"""Worker: jalankan terus, ambil satu job per waktu.

Satu job dijalankan penuh (semua tahap) sebelum job berikutnya diambil.
  topaz_only : topaz -> done
  topaz_cc   : topaz -> ae (.mov) -> encoding HandBrake (.mp4) -> done

Jalankan: python -m app.worker
Tes tanpa GPU/AE: FAKE_TOPAZ=1 FAKE_AE=1 FAKE_HANDBRAKE=1 python -m app.worker
"""

import time
from datetime import datetime
from pathlib import Path

from app import config, db
from app.ae import run_ae
from app.handbrake import run_encode
from app.proc import ToolError
from app.topaz import run_upscale


def log(msg):
    ts = datetime.now().isoformat(timespec="milliseconds")
    print(f"[{ts}] {msg}", flush=True)


def final_path(job):
    # topaz_cc keluar dari HandBrake sebagai mp4; topaz_only tetap memakai ext asli
    ext = "mp4" if job["service"] == "topaz_cc" else job["ext"]
    return config.OUTPUT_DIR / f"{job['id']}.{ext}"


def run_stage(job_id, stage, fn, args, intermediate=None):
    """Satu tahap: catat stage (dan file perantara) di DB, jalankan, lalu catat waktu mulai dan selesai."""
    db.set_stage(job_id, stage)
    if intermediate is not None:
        db.set_intermediate_path(job_id, intermediate)
    log(f"job {job_id} stage {stage} start")
    fn(*args)
    log(f"job {job_id} stage {stage} end")


def run_pipeline(job):
    job_id = job["id"]
    input_path = Path(job["input_path"])
    output = final_path(job)

    if job["service"] == "topaz_only":
        run_stage(job_id, "topaz", run_upscale, (input_path, output, config.JOB_TIMEOUT_SEC))
        return output

    topaz_out = config.INTERMEDIATE_DIR / f"{job_id}_topaz.{job['ext']}"
    ae_out = config.INTERMEDIATE_DIR / f"{job_id}_ae.mov"
    preset = config.get_cc_preset(job["cc_preset"])
    run_stage(job_id, "topaz", run_upscale,
              (input_path, topaz_out, config.JOB_TIMEOUT_SEC), intermediate=topaz_out)
    run_stage(job_id, "ae", run_ae,
              (topaz_out, ae_out, preset, config.JOB_TIMEOUT_SEC), intermediate=ae_out)
    run_stage(job_id, "encoding", run_encode,
              (ae_out, output, config.JOB_TIMEOUT_SEC))
    return output


def cleanup_intermediates(job_id):
    """Hapus file perantara milik job ini, baik job selesai maupun gagal."""
    for path in config.INTERMEDIATE_DIR.glob(f"{job_id}_*"):
        try:
            path.unlink()
        except OSError as e:
            log(f"job {job_id} gagal hapus perantara: {type(e).__name__}")
    db.set_intermediate_path(job_id, None)


def process_job(job):
    job_id = job["id"]
    try:
        output = run_pipeline(job)
    except ToolError as e:
        db.mark_failed(job_id, str(e))
        log(f"job {job_id} failed: {e}")
    except Exception as e:  # error tak terduga: tandai failed, worker tetap hidup
        db.mark_failed(job_id, f"error tak terduga: {type(e).__name__}")
        log(f"job {job_id} failed (unexpected): {e!r}")
    else:
        db.mark_done(job_id, output)
        log(f"job {job_id} done")
    finally:
        cleanup_intermediates(job_id)


def main():
    db.init_db()
    requeued, failed = db.reset_processing_jobs()
    if requeued or failed:
        log(f"recovery: {requeued} dikembalikan ke queued, {failed} ditandai failed")
    log("worker start")
    while True:
        job = db.claim_next_job()
        if job is None:
            time.sleep(config.POLL_INTERVAL_SEC)
            continue
        log(f"job {job['id']} processing")
        process_job(job)


if __name__ == "__main__":
    main()
