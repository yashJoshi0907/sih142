"""
sr_api.py — Thin API surface for the ARGUS frontend.

Reuses the existing pipeline pieces (database repositories, tools, model
registry) instead of duplicating them. Run alongside app.py's Streamlit shell
or standalone:

    uvicorn sr_api:app --port 8000
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from database import init_db, SessionLocal, JobRepository, MetricsRepository
from tools import run_super_resolution, compute_metrics, geotiff_to_png, upscale_geotiff
from models import MODEL_REGISTRY
from models.bicubic import run_bicubic

init_db()
os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)
os.makedirs("outputs/thumbs", exist_ok=True)

app = FastAPI(title="ARGUS SR API", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Job id -> stage string, read by the SSE stream while the worker works.
_PROGRESS: dict[int, str] = {}


def _set_stage(job_id: int, stage: str) -> None:
    _PROGRESS[job_id] = stage


# ─── Models ───────────────────────────────────────────────────────────────────

@app.get("/api/models")
def list_models():
    return {
        name: {
            "scale": info["scale"],
            "output_res_m": info["output_res_m"],
            "description": info["description"],
            "physical_bias": info["physical_bias"],
            "paper": info["paper"],
        }
        for name, info in MODEL_REGISTRY.items()
    }


# ─── Submission ───────────────────────────────────────────────────────────────

@app.post("/api/process")
async def process(
    file: Optional[UploadFile] = File(None),
    use_sample: bool = Form(False),
    model_name: str = Form("LDSR-S2 (ESA)"),
):
    if model_name not in MODEL_REGISTRY:
        raise HTTPException(400, f"Unknown model. Choose from: {list(MODEL_REGISTRY.keys())}")

    if use_sample or file is None:
        sample = Path("static/sample_data/sample_sentinel2.tif")
        if not sample.exists():
            import subprocess
            import sys

            try:
                subprocess.run(
                    [sys.executable, "generate_sample_tile.py"], check=True, timeout=120
                )
            except Exception as e:  # pragma: no cover - environment dependent
                raise HTTPException(500, f"Could not generate sample tile: {e}")
        input_path = str(sample)
        filename = sample.name
    else:
        input_path = f"uploads/{file.filename}"
        with open(input_path, "wb") as buf:
            while chunk := await file.read(1 << 20):
                buf.write(chunk)
        filename = file.filename or "tile.tif"

    minfo = MODEL_REGISTRY[model_name]
    db = SessionLocal()
    try:
        job = JobRepository(db).create(
            filename=filename,
            sr_model=model_name,
            scale_factor=float(minfo["scale"]),
            input_path=input_path,
        )
        job_id = job.id
    finally:
        db.close()

    asyncio.get_running_loop().run_in_executor(None, _process_job, job_id, input_path, model_name)
    return {"job_id": job_id, "status": "queued", "model": model_name}


def _process_job(job_id: int, input_path: str, model_name: str) -> None:
    """Worker: runs the selected SR model, scores it, commits to the DB."""
    db = SessionLocal()
    job_repo = JobRepository(db)
    met_repo = MetricsRepository(db)
    try:
        stem = Path(input_path).stem
        safe_m = model_name.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "")
        out_sr = f"outputs/sr_{job_id}_{safe_m}.tif"
        out_bic = f"outputs/bicubic_{job_id}.tif"

        _set_stage(job_id, "reading")
        job_repo.update_status(job_id, "running")

        t0 = time.time()
        _set_stage(job_id, "super-resolution")
        result = run_super_resolution(input_path, out_sr, model_name=model_name)

        _set_stage(job_id, "control")
        scale = int(MODEL_REGISTRY[model_name]["scale"])
        run_bicubic(input_path, out_bic, scale_factor=scale)

        _set_stage(job_id, "scoring")
        metrics = compute_metrics(out_sr, out_bic)

        # Preview thumbnails for the console.
        _set_stage(job_id, "rendering")
        geotiff_to_png(input_path, f"outputs/thumbs/in_{job_id}.png")
        geotiff_to_png(out_sr, f"outputs/thumbs/sr_{job_id}.png")

        elapsed = time.time() - t0
        job_repo.update_status(job_id, "done", output_path=out_sr)
        met_repo.save(
            job_id=job_id,
            psnr=metrics["psnr"],
            ssim=metrics["ssim"],
            inference_time=elapsed,
            output_res_m=MODEL_REGISTRY[model_name]["output_res_m"],
        )
    except Exception as e:
        job_repo.update_status(job_id, "failed", error_msg=str(e))
    finally:
        db.close()
        _PROGRESS.pop(job_id, None)


# ─── Job status & products ────────────────────────────────────────────────────

@app.get("/api/job/{job_id}")
def get_job(job_id: int):
    db = SessionLocal()
    try:
        job = JobRepository(db).get(job_id)
    finally:
        db.close()
    if not job:
        raise HTTPException(404, "Job not found")
    return {
        "job_id": job.id,
        "status": job.status,
        "model": job.sr_model,
        "filename": job.filename,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error": job.error_msg,
    }


@app.get("/api/job/{job_id}/download")
def download_job(job_id: int):
    db = SessionLocal()
    try:
        job = JobRepository(db).get(job_id)
    finally:
        db.close()
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != "done":
        raise HTTPException(400, f"Job not done yet (status: {job.status})")
    if not job.output_path or not Path(job.output_path).exists():
        raise HTTPException(404, "Output file not found")
    return FileResponse(
        job.output_path, media_type="image/tiff", filename=Path(job.output_path).name
    )


@app.get("/api/job/{job_id}/thumbnail")
def job_thumbnail(job_id: int, kind: str = "sr"):
    name = f"in_{job_id}.png" if kind == "input" else f"sr_{job_id}.png"
    path = Path("outputs/thumbs") / name
    if not path.exists():
        raise HTTPException(404, "Thumbnail not available yet")
    return FileResponse(path, media_type="image/png", filename=name)


@app.get("/api/metrics/{job_id}")
def get_metrics(job_id: int):
    db = SessionLocal()
    try:
        m = MetricsRepository(db).get_by_job(job_id)
    finally:
        db.close()
    if not m:
        raise HTTPException(404, "Metrics not found for this job")
    return {
        "job_id": job_id,
        "psnr_vs_bicubic_db": m.psnr_vs_bicubic,
        "ssim_vs_bicubic": m.ssim_vs_bicubic,
        "inference_time_sec": m.inference_time_sec,
        "output_resolution_m": m.output_resolution_m,
        "hallucination_score": m.hallucination_score,
    }


@app.get("/api/history")
def history(limit: int = 50):
    db = SessionLocal()
    try:
        jobs = JobRepository(db).list_all(limit=limit)
    finally:
        db.close()
    return [
        {
            "job_id": j.id,
            "filename": j.filename,
            "status": j.status,
            "model": j.sr_model,
            "created_at": j.created_at.isoformat() if j.created_at else None,
        }
        for j in jobs
    ]


# ─── SSE progress stream ──────────────────────────────────────────────────────

@app.get("/api/progress/{job_id}")
async def progress_stream(job_id: int):
    """Server-sent events: stage ticks while running, `done` with final status."""

    async def gen():
        last_stage = None
        while True:
            db = SessionLocal()
            try:
                job = JobRepository(db).get(job_id)
            finally:
                db.close()

            if not job:
                yield _sse("done", {"error": "Job not found"})
                return

            stage = _PROGRESS.get(job_id, job.status)
            if stage != last_stage:
                last_stage = stage
                yield _sse("progress", {"percent": None, "stage": stage, "message": stage})

            if job.status in ("done", "failed"):
                yield _sse(
                    "done",
                    {
                        "job_id": job.id,
                        "status": job.status,
                        "model": job.sr_model,
                        "filename": job.filename,
                        "created_at": job.created_at.isoformat() if job.created_at else None,
                        "completed_at": (
                            job.completed_at.isoformat() if job.completed_at else None
                        ),
                        "error": job.error_msg,
                    },
                )
                return
            await asyncio.sleep(0.7)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
